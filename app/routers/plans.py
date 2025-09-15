from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.db import get_db

router = APIRouter(prefix="/admin")


@router.post("/plans", response_model=schemas.MatchPlan, summary="플랜 생성")
def create_plan(plan: schemas.MatchPlanCreate, db: Session = Depends(get_db)):
    """매칭 플랜 생성 엔드포인트.

    Args:
        plan (schemas.MatchPlanCreate): 생성할 플랜 정보.
        db (Session): Depends(get_db)로 제공되는 데이터베이스 세션.

    Returns:
        schemas.MatchPlan: 생성된 플랜 객체(또는 crud 구현에 따름).
    """
    return crud.create_plan(db, plan)


@router.get("/plans", response_model=List[schemas.MatchPlan], summary="플랜 목록 조회")
def list_plans(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """플랜 목록 조회 엔드포인트.

    Args:
        skip (int): 페이지 오프셋.
        limit (int): 최대 반환 개수.
        db (Session): Depends(get_db)로 제공되는 데이터베이스 세션.

    Returns:
        List[schemas.MatchPlan]: 플랜 목록.
    """
    return crud.list_plans(db, skip=skip, limit=limit)


@router.get("/plans/{plan_id}", response_model=schemas.MatchPlan, summary="플랜 조회")
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    """단일 플랜 조회 엔드포인트.

    Args:
        plan_id (int): 조회할 플랜 ID.
        db (Session): Depends(get_db)로 제공되는 데이터베이스 세션.

    Returns:
        schemas.MatchPlan: 조회된 플랜.

    Raises:
        HTTPException: 플랜이 존재하지 않을 경우 404 반환.
    """
    plan = crud.get_plan(db, plan_id=plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan
