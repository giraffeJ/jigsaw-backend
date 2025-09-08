from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .db import SessionLocal, engine

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="매칭 시스템 API", description="소개팅 매칭 시스템을 위한 FastAPI 백엔드", version="1.0.0"
)


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def read_root():
    return {"message": "매칭 시스템 API에 오신 것을 환영합니다!"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# User endpoints
@app.post("/users/", response_model=schemas.User, summary="사용자 등록")
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """새로운 사용자를 등록합니다."""
    try:
        return crud.create_user(db=db, user=user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/users/", response_model=List[schemas.UserPublic], summary="사용자 목록 조회")
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """활성 사용자 목록을 조회합니다 (공개 정보만)."""
    users = crud.get_users(db, skip=skip, limit=limit)
    return users


@app.get("/users/{user_id}", response_model=schemas.User, summary="사용자 상세 조회")
def read_user(user_id: int, db: Session = Depends(get_db)):
    """특정 사용자의 상세 정보를 조회합니다."""
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    return db_user


@app.put("/users/{user_id}", response_model=schemas.User, summary="사용자 정보 수정")
def update_user(user_id: int, user: schemas.UserUpdate, db: Session = Depends(get_db)):
    """사용자 정보를 수정합니다."""
    db_user = crud.update_user(db, user_id=user_id, user=user)
    if db_user is None:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    return db_user


@app.delete("/users/{user_id}", summary="사용자 비활성화")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """사용자를 비활성화합니다."""
    success = crud.delete_user(db, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    return {"message": "사용자가 비활성화되었습니다"}


# Matching endpoints
@app.get(
    "/users/{user_id}/matches", response_model=List[schemas.UserPublic], summary="매칭 후보 조회"
)
def get_user_matches(user_id: int, skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """특정 사용자의 매칭 후보를 조회합니다."""
    # 사용자 존재 확인
    user = crud.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

    # 매칭 후보 조회 (본인 제외)
    matches = crud.get_users_for_matching(db, exclude_user_id=user_id, skip=skip, limit=limit)
    return matches


@app.get("/search/users", response_model=List[schemas.UserPublic], summary="조건별 사용자 검색")
def search_users(
    birth_year_min: Optional[int] = Query(None, description="최소 출생연도"),
    birth_year_max: Optional[int] = Query(None, description="최대 출생연도"),
    height_min: Optional[int] = Query(None, description="최소 키"),
    height_max: Optional[int] = Query(None, description="최대 키"),
    residence: Optional[str] = Query(None, description="거주지 (부분 검색)"),
    education_level: Optional[str] = Query(None, description="학력"),
    religion: Optional[str] = Query(None, description="종교"),
    smoking_status: Optional[str] = Query(None, description="흡연 여부"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """조건에 따라 사용자를 검색합니다."""
    users = crud.search_users_by_criteria(
        db=db,
        birth_year_min=birth_year_min,
        birth_year_max=birth_year_max,
        height_min=height_min,
        height_max=height_max,
        residence=residence,
        education_level=education_level,
        religion=religion,
        smoking_status=smoking_status,
        skip=skip,
        limit=limit,
    )
    return users
