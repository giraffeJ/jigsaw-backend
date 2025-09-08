from typing import List

from fastapi import APIRouter, Depends, HTTPException
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


@router.post("/match/plans", response_model=schemas.MatchPlan, summary="플랜 생성")
def create_plan(plan: schemas.MatchPlanCreate, db: Session = Depends(get_db)):
    return crud.create_plan(db, plan)


@router.get("/match/plans", response_model=List[schemas.MatchPlan], summary="플랜 목록 조회")
def list_plans(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return crud.list_plans(db, skip=skip, limit=limit)


@router.get("/match/plans/{plan_id}", response_model=schemas.MatchPlan, summary="플랜 조회")
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = crud.get_plan(db, plan_id=plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan
