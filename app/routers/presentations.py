"""프레젠테이션(제안) 관련 관리자 엔드포인트.

프레젠테이션 생성, 결정(수락/거절), 사용자별 프레젠테이션 조회 및
관리자가 전달해야 할 대기중인 렌더된 메시지 목록 조회를 제공합니다.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud, schemas
from app.db import get_db

router = APIRouter(prefix="/admin")


@router.post(
    "/presentations", response_model=schemas.Presentation, summary="프레젠테이션(제안) 생성"
)
def create_presentation(presentation: schemas.PresentationCreate, db: Session = Depends(get_db)):
    """프레젠테이션(제안) 생성 엔드포인트.

    Args:
        presentation (schemas.PresentationCreate): 생성할 프레젠테이션 데이터.
        db (Session): Depends(get_db)로 제공되는 데이터베이스 세션.

    Returns:
        schemas.Presentation: 생성된 Presentation 객체 (crud 구현에 따름).
    """
    return crud.create_presentation(db, presentation)


@router.post(
    "/presentations/{presentation_id}/decision",
    response_model=schemas.Presentation,
    summary="프레젠테이션 결정(수락/거절)",
)
def decide_presentation(
    presentation_id: int, decision: schemas.PresentationDecision, db: Session = Depends(get_db)
):
    """프레젠테이션 결정(수락/거절) 엔드포인트.

    Args:
        presentation_id (int): 결정할 Presentation의 ID.
        decision (schemas.PresentationDecision): 결정 정보(수락/거절 등).
        db (Session): Depends(get_db)로 제공되는 데이터베이스 세션.

    Returns:
        schemas.Presentation: 업데이트된 Presentation 객체.

    Raises:
        HTTPException: 해당 Presentation이 존재하지 않으면 404 반환.
    """
    p = crud.decide_presentation(db, presentation_id=presentation_id, decision=decision)
    if not p:
        raise HTTPException(status_code=404, detail="Presentation not found")
    return p


@router.get(
    "/presentations",
    response_model=List[schemas.Presentation],
    summary="프레젠테이션 목록 조회 (user_id, role)",
)
def list_presentations(
    user_id: int = Query(..., description="사용자 ID"),
    role: Optional[str] = Query("requester", description="requester 또는 candidate"),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """사용자별 프레젠테이션 목록 조회.

    Args:
        user_id (int): 조회 대상 사용자 ID (필수 쿼리 파라미터).
        role (Optional[str]): "requester" 또는 "candidate" 중 하나를 지정.
        skip (int): 페이지 오프셋.
        limit (int): 최대 반환 개수.
        db (Session): Depends(get_db)로 제공되는 데이터베이스 세션.

    Returns:
        List[schemas.Presentation]: 해당 사용자와 역할에 대한 프레젠테이션 목록.
    """
    role_val = "requester" if role != "candidate" else "candidate"
    return crud.list_presentations_for_user(
        db, user_id=user_id, role=role_val, skip=skip, limit=limit
    )


@router.get(
    "/presentations/pending_messages",
    response_model=List[schemas.Presentation],
    summary="관리자가 전달할 대기중인 매칭 문구 목록 (rendered_message 포함)",
)
def list_pending_messages(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """관리자가 전달해야 할 대기 중인 렌더된 메시지(프레젠테이션) 목록 조회.

    Args:
        skip (int): 페이지 오프셋.
        limit (int): 최대 반환 개수.
        db (Session): Depends(get_db)로 제공되는 데이터베이스 세션.

    Returns:
        List[schemas.Presentation]: rendered_message가 존재하고 전달 대기중인 Presentation 목록,
            오래된 순으로 정렬되어 반환됩니다.
    """
    items = crud.list_pending_presentations(db, skip=skip, limit=limit)
    return items
