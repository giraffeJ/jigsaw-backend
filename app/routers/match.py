"""매칭 엔드포인트

단일 및 벌크 매칭 엔드포인트를 제공합니다. 각 핸들러는 요청/응답 형식, 예시,
및 가능한 HTTP 오류(4xx/5xx)를 문서화합니다.
"""

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.manager import history_manager, template_manager, user_manager
from app.models.match_response import (
    BulkMatchCandidate,
    BulkMatchOut,
    SingleMatchCandidate,
    SingleMatchOut,
)
from app.services.match_service import MatchService

router = APIRouter(prefix="/match", tags=["match"])


@router.post(
    "/single",
    response_model=SingleMatchOut,
    summary="단일 추천(읽기 전용)",
)
def single_match(
    body: dict = Body(...),
    db: Session = Depends(get_db),
):
    """단일 사용자에 대한 매칭 후보를 조회합니다.

    Args:
        body (dict): 요청 본문으로 다음 중 하나를 포함해야 합니다:
            - "user_id" (int | None): 매칭 대상 사용자의 ID
            - "nickname" (str | None): 매칭 대상 사용자의 닉네임
        db (Session): Depends(get_db)로 제공되는 데이터베이스 세션

    Returns:
        SingleMatchOut: 대상 사용자 정보(user_id 또는 nickname)와 추천 후보 목록(각 후보는 id, nickname, 채워진 템플릿 포함)을 반환합니다.

    Raises:
        HTTPException: 입력값이 유효하지 않거나(예: user_id와 nickname이 모두 누락) 내부 검증 실패 시 400을 반환합니다.
        HTTPException: 대상 사용자를 찾을 수 없거나, 템플릿(id=1)이 없으면 404를 반환합니다.

    Example:
        POST /match/single
        {
            "user_id": 123
        }

    Notes:
        - user_id 또는 nickname 중 하나는 반드시 제공되어야 합니다.
        - 내부 매칭 로직은 :class:`app.services.match_service.MatchService`에 위임됩니다.
        - 템플릿 id=1을 조회해 채워진 템플릿을 생성합니다.
    """
    user_id = body.get("user_id")
    nickname = body.get("nickname")

    svc = MatchService(user_manager, history_manager, template_manager)

    # Resolve subject user for returning user_id/nickname in the response
    subject = None
    if user_id is not None:
        subject = user_manager.get_by_id(db, int(user_id))
    if subject is None and nickname is not None:
        subject = user_manager.get_by_nickname(db, str(nickname))
    if subject is None:
        raise HTTPException(status_code=404, detail="subject user not found")

    try:
        candidates_meta = svc.single_match(db, user_id=user_id, nickname=nickname)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Template id=1 lookup (raises ValueError -> 404)
    try:
        tmpl = svc.get_template_for_id_1(db)
    except ValueError:
        raise HTTPException(status_code=404, detail="template id=1 not found")

    candidates_out = []
    for cand_user, _score in candidates_meta:
        profile_url = getattr(cand_user, "profile_url", "") or ""
        filled = svc.fill_template(tmpl.content, profile_url)
        candidates_out.append(
            SingleMatchCandidate(
                id=cand_user.id, nickname=cand_user.nickname, filled_template=filled
            )
        )

    return SingleMatchOut(
        user_id=subject.id if subject is not None else None,
        nickname=subject.nickname if subject is not None else None,
        candidates=candidates_out,
    )


@router.get(
    "/bulk",
    response_model=BulkMatchOut,
    summary="전체(벌크) 추천(읽기 전용)",
)
def bulk_match(db: Session = Depends(get_db)):
    """모든 활성 사용자에 대해 벌크 추천을 생성합니다.

    Args:
        db (Session): Depends(get_db)로 제공되는 데이터베이스 세션.

    Returns:
        BulkMatchOut: 각 대상 사용자(subject)에 대한 추천 항목 리스트를 포함합니다.
            각 항목은 추천 사용자(id, nickname)와 채워진 템플릿을 포함하거나,
            추천이 없을 경우 None 값을 가집니다.

    Raises:
        HTTPException: 채워진 템플릿 생성을 위한 템플릿(id=1)이 없을 경우 404를 반환합니다.

    Notes:
        - 이 엔드포인트는 읽기 전용이며 배정 로직은 :class:`app.services.match_service.MatchService`에 위임됩니다.
        - 결과는 id=1 템플릿을 사용해 채워집니다; 템플릿이 없으면 404가 발생합니다.
    """
    svc = MatchService(user_manager, history_manager, template_manager)

    assignments = svc.bulk_match(db)

    try:
        tmpl = svc.get_template_for_id_1(db)
    except ValueError:
        raise HTTPException(status_code=404, detail="template id=1 not found")

    items = []
    for subject, recommended in assignments:
        if recommended is None:
            items.append(
                BulkMatchCandidate(
                    for_user_id=subject.id,
                    for_user_nickname=subject.nickname,
                    recommended_id=None,
                    recommended_nickname=None,
                    filled_template=None,
                )
            )
            continue
        profile_url = getattr(recommended, "profile_url", "") or ""
        filled = svc.fill_template(tmpl.content, profile_url)
        items.append(
            BulkMatchCandidate(
                for_user_id=subject.id,
                for_user_nickname=subject.nickname,
                recommended_id=recommended.id,
                recommended_nickname=recommended.nickname,
                filled_template=filled,
            )
        )

    return BulkMatchOut(items=items)
