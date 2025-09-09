from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.db import SessionLocal
from app.services.matching import mutual_candidates


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


router = APIRouter()


@router.get(
    "/users/{user_id}/candidates",
    response_model=schemas.CandidatesResponse,
    summary="상호 선호 + 분포 매칭 후보",
)
def get_candidates(
    user_id: int, limit: int = 3, cooldown_days: int = 30, db: Session = Depends(get_db)
):
    user = crud.get_user(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    items = mutual_candidates(db, user, cooldown_days=cooldown_days, limit=limit)
    return schemas.CandidatesResponse(items=items)


@router.post(
    "/admin/match/plans/{plan_id}/fill",
    response_model=schemas.PlanPreview,
    summary="배치 매칭 플랜 미리보기(저장 안 함)",
)
def fill_plan(
    plan_id: int, per_user_limit: int = 1, cooldown_days: int = 30, db: Session = Depends(get_db)
):
    plan = crud.get_plan(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    users = crud.get_users(db, skip=0, limit=10_000)
    items = []
    for u in users:
        cand = mutual_candidates(db, u, cooldown_days=cooldown_days, limit=per_user_limit)
        items.append({"user_id": u.id, "proposals": cand})
    return schemas.PlanPreview(plan_id=plan_id, items=items)
