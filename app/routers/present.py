from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.db import SessionLocal
from app.services.matching import mutual_candidates
from app.services.template_engine import default_params, render_string

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/users/{user_id}/present",
    response_model=schemas.PresentResponse,
    summary="단일 제안 생성(확정 아님)",
)
def present_single(user_id: int, body: schemas.PresentRequest, db: Session = Depends(get_db)):
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
