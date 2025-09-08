from typing import List, Optional

from sqlalchemy.orm import Session

from . import models, schemas


# User CRUD operations
def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_kakao_id(db: Session, kakao_id: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.kakao_id == kakao_id).first()


def get_user_by_phone(db: Session, phone_number: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.phone_number == phone_number).first()


def get_user_by_nickname(db: Session, nickname: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.nickname == nickname).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    return (
        db.query(models.User).filter(models.User.is_active == True).offset(skip).limit(limit).all()
    )


def get_users_for_matching(
    db: Session, exclude_user_id: int, skip: int = 0, limit: int = 100
) -> List[models.User]:
    """매칭용 사용자 목록 조회 (본인 제외, 활성 사용자만)"""
    return (
        db.query(models.User)
        .filter(
            models.User.id != exclude_user_id,
            models.User.is_active == True,
            models.User.privacy_consent == True,
            models.User.confidentiality_consent == True,
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    # 중복 체크
    existing_kakao = get_user_by_kakao_id(db, user.kakao_id)
    if existing_kakao:
        raise ValueError("이미 등록된 카카오톡 ID입니다.")

    existing_phone = get_user_by_phone(db, user.phone_number)
    if existing_phone:
        raise ValueError("이미 등록된 전화번호입니다.")

    db_user = models.User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, user: schemas.UserUpdate) -> Optional[models.User]:
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        update_data = user.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_user, field, value)
        db.commit()
        db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int) -> bool:
    """사용자 비활성화 (실제 삭제 대신)"""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        db_user.is_active = False
        db.commit()
        return True
    return False


def search_users_by_criteria(
    db: Session,
    birth_year_min: Optional[int] = None,
    birth_year_max: Optional[int] = None,
    height_min: Optional[int] = None,
    height_max: Optional[int] = None,
    residence: Optional[str] = None,
    education_level: Optional[str] = None,
    religion: Optional[str] = None,
    smoking_status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[models.User]:
    """매칭 조건에 따른 사용자 검색"""
    query = db.query(models.User).filter(
        models.User.is_active == True,
        models.User.privacy_consent == True,
        models.User.confidentiality_consent == True,
    )

    if birth_year_min:
        query = query.filter(models.User.birth_year >= birth_year_min)
    if birth_year_max:
        query = query.filter(models.User.birth_year <= birth_year_max)
    if height_min:
        query = query.filter(models.User.height >= height_min)
    if height_max:
        query = query.filter(models.User.height <= height_max)
    if residence:
        query = query.filter(models.User.residence.contains(residence))
    if education_level:
        query = query.filter(models.User.education_level == education_level)
    if religion:
        query = query.filter(models.User.religion == religion)
    if smoking_status:
        query = query.filter(models.User.smoking_status == smoking_status)

    return query.offset(skip).limit(limit).all()
