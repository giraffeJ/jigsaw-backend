from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud, schemas
from app.db import SessionLocal


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


router = APIRouter(prefix="/admin")


@router.post(
    "/presentations", response_model=schemas.Presentation, summary="프레젠테이션(제안) 생성"
)
def create_presentation(presentation: schemas.PresentationCreate, db: Session = Depends(get_db)):
    return crud.create_presentation(db, presentation)


@router.post(
    "/presentations/{presentation_id}/decision",
    response_model=schemas.Presentation,
    summary="프레젠테이션 결정(수락/거절)",
)
def decide_presentation(
    presentation_id: int, decision: schemas.PresentationDecision, db: Session = Depends(get_db)
):
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
    role_val = "requester" if role != "candidate" else "candidate"
    return crud.list_presentations_for_user(
        db, user_id=user_id, role=role_val, skip=skip, limit=limit
    )
