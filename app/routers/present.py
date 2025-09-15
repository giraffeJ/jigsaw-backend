"""프리젠테이션(제안) 관련 엔드포인트.

단일 제안 생성 및 배치 플랜 제안 생성(커밋용)을 제공합니다. 템플릿 렌더링과
프레젠테이션 레코드 생성 로직을 포함하며, 렌더링 실패나 리소스 미존재시 적절한
HTTPException을 발생시킵니다.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.db import get_db
from app.services.matching import mutual_candidates
from app.services.template_engine import default_params, render_string

router = APIRouter()


@router.post(
    "/users/{user_id}/present",
    response_model=schemas.PresentResponse,
    summary="단일 제안 생성(확정 아님)",
)
def present_single(user_id: int, body: schemas.PresentRequest, db: Session = Depends(get_db)):
    """단일 제안 생성 (확정 아님).

    Args:
        user_id (int): 제안 요청자 사용자 ID (경로 매개변수).
        body (schemas.PresentRequest): 후보자 ID, 템플릿 키/버전, 추가 파라미터 등을 포함한 요청 본문.
        db (Session): Depends(get_db)로 제공되는 데이터베이스 세션.

    Returns:
        schemas.PresentResponse: 생성된 프레젠테이션의 ID, 렌더링된 메시지, outcome, presented_at 등을 포함합니다.

    Raises:
        HTTPException: 요청자 또는 후보자/템플릿 미존재 시 404를 반환합니다.
        HTTPException: 템플릿 렌더링 실패 시 400을 반환합니다.

    Notes:
        - 템플릿 조회는 key/version 기준으로 수행되며, 활성화된 템플릿이어야 합니다.
        - 프레젠테이션 생성은 crud.create_presentation_with_rendered에 위임합니다.
    """
    requester = crud.get_user(db, user_id)
    candidate = crud.get_user(db, body.candidate_id)
    if not requester or not candidate:
        raise HTTPException(status_code=404, detail="User not found")
    tmpl = crud.get_template_by_key_version(db, body.template_key, body.template_version)
    if not tmpl or not tmpl.is_active:
        raise HTTPException(status_code=404, detail="Template not found")
    params = {**default_params(requester, candidate), **(body.extra_params or {})}
    try:
        rendered = render_string(tmpl.content, params)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Render error: {e}")
    pres = crud.create_presentation_with_rendered(
        db,
        requester_id=requester.id,
        candidate_id=candidate.id,
        plan_id=None,
        template_key=tmpl.key,
        template_version=tmpl.version,
        rendered_message=rendered,
    )
    outcome = pres.outcome.value if hasattr(pres.outcome, "value") else pres.outcome
    return schemas.PresentResponse(
        presentation_id=pres.id,
        rendered_message=rendered,
        outcome=outcome,
        presented_at=pres.presented_at,
    )


@router.post("/admin/match/plans/{plan_id}/present", summary="배치 플랜 제안 commit(확정 아님)")
def present_plan(plan_id: int, body: schemas.PlanPresentQuery, db: Session = Depends(get_db)):
    """배치 플랜 기반 제안 생성 (확정 아님).

    Args:
        plan_id (int): 처리할 플랜의 ID (경로 매개변수).
        body (schemas.PlanPresentQuery): per_user_limit, cooldown_days, template 정보, dry_run 등 옵션을 포함.
        db (Session): Depends(get_db)로 제공되는 데이터베이스 세션.

    Returns:
        dict: {"plan_id": plan_id, "items": [...] } 형태의 결과. 각 항목은 user_id, candidate_id,
              렌더된 메시지 또는 오류 정보를 포함합니다.

    Raises:
        HTTPException: 플랜이 존재하지 않거나(404), 템플릿이 없거나 비활성일 경우 404를 반환합니다.

    Notes:
        - dry_run=True인 경우 DB에 저장하지 않고 렌더된 메시지만 결과에 포함합니다.
        - 렌더링 실패 항목은 결과에 error 필드로 기록됩니다.
    """
    plan = crud.get_plan(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    tmpl = crud.get_template_by_key_version(db, body.template_key, body.template_version)
    if not tmpl or not tmpl.is_active:
        raise HTTPException(status_code=404, detail="Template not found")

    users = crud.get_users(db, skip=0, limit=10_000)
    results = []
    for u in users:
        cands = mutual_candidates(
            db, u, cooldown_days=body.cooldown_days, limit=body.per_user_limit
        )
        if not cands:
            continue
        for c in cands:
            cand_user = crud.get_user(db, c["candidate_id"])
            if not cand_user:
                continue
            params = {**default_params(u, cand_user), **(body.extra_params or {})}
            try:
                rendered = render_string(tmpl.content, params)
            except Exception as e:
                # skip this candidate and record error
                results.append({"user_id": u.id, "candidate_id": cand_user.id, "error": str(e)})
                continue
            if not body.dry_run:
                pres = crud.create_presentation_with_rendered(
                    db,
                    requester_id=u.id,
                    candidate_id=cand_user.id,
                    plan_id=plan.id,
                    template_key=tmpl.key,
                    template_version=tmpl.version,
                    rendered_message=rendered,
                )
                results.append(
                    {
                        "user_id": u.id,
                        "presentation_id": pres.id,
                        "candidate_id": cand_user.id,
                        "message": rendered,
                    }
                )
            else:
                results.append({"user_id": u.id, "candidate_id": cand_user.id, "message": rendered})
    return {"plan_id": plan_id, "items": results}
