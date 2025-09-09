from datetime import datetime
from typing import Dict, List, Literal, Optional

from sqlalchemy import func
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

    # normalize enum-like fields so SQLAlchemy Enum columns receive enum members
    data = user.dict()
    # Normalize enum-like fields so SQLAlchemy Enum columns receive enum members
    if "education_level" in data and data["education_level"] is not None:
        try:
            data["education_level"] = models.EducationLevel(data["education_level"])
        except Exception:
            pass
    if "religion" in data and data["religion"] is not None:
        try:
            data["religion"] = models.Religion(data["religion"])
        except Exception:
            pass
    if "smoking_status" in data and data["smoking_status"] is not None:
        try:
            data["smoking_status"] = models.SmokingStatus(data["smoking_status"])
        except Exception:
            pass
    if "workplace_matching" in data and data["workplace_matching"] is not None:
        try:
            data["workplace_matching"] = models.WorkplaceMatching(data["workplace_matching"])
        except Exception:
            pass

    # preferred_smoking and preferred_religion may be provided as lists in schemas;
    # store them as comma-separated strings in the DB (e.g. "비흡연,전자담배")
    if "preferred_smoking" in data and data["preferred_smoking"] is not None:
        val = data["preferred_smoking"]
        if isinstance(val, (list, tuple)):
            data["preferred_smoking"] = ",".join([str(x).strip() for x in val if x is not None])
        else:
            data["preferred_smoking"] = str(val).strip()

    if "preferred_religion" in data and data["preferred_religion"] is not None:
        val = data["preferred_religion"]
        if isinstance(val, (list, tuple)):
            data["preferred_religion"] = ",".join([str(x).strip() for x in val if x is not None])
        else:
            data["preferred_religion"] = str(val).strip()

    db_user = models.User(**data)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, user: schemas.UserUpdate) -> Optional[models.User]:
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        update_data = user.dict(exclude_unset=True)
        # normalize enum-like fields before applying
        if "education_level" in update_data and update_data["education_level"] is not None:
            try:
                update_data["education_level"] = models.EducationLevel(
                    update_data["education_level"]
                )
            except Exception:
                pass
        if "religion" in update_data and update_data["religion"] is not None:
            try:
                update_data["religion"] = models.Religion(update_data["religion"])
            except Exception:
                pass
        if "smoking_status" in update_data and update_data["smoking_status"] is not None:
            try:
                update_data["smoking_status"] = models.SmokingStatus(update_data["smoking_status"])
            except Exception:
                pass
        if "workplace_matching" in update_data and update_data["workplace_matching"] is not None:
            try:
                update_data["workplace_matching"] = models.WorkplaceMatching(
                    update_data["workplace_matching"]
                )
            except Exception:
                pass

        # preferred_smoking/preferred_religion may be provided as lists; convert to CSV strings
        if "preferred_smoking" in update_data and update_data["preferred_smoking"] is not None:
            val = update_data["preferred_smoking"]
            if isinstance(val, (list, tuple)):
                update_data["preferred_smoking"] = ",".join(
                    [str(x).strip() for x in val if x is not None]
                )
            else:
                update_data["preferred_smoking"] = str(val).strip()

        if "preferred_religion" in update_data and update_data["preferred_religion"] is not None:
            val = update_data["preferred_religion"]
            if isinstance(val, (list, tuple)):
                update_data["preferred_religion"] = ",".join(
                    [str(x).strip() for x in val if x is not None]
                )
            else:
                update_data["preferred_religion"] = str(val).strip()

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


# --- Templates CRUD ---
def create_template(db: Session, tmpl: schemas.TemplateCreate) -> models.Template:
    existing = (
        db.query(models.Template)
        .filter(models.Template.key == tmpl.key, models.Template.version == tmpl.version)
        .first()
    )
    if existing:
        raise ValueError("template with key+version already exists")
    db_tmpl = models.Template(**tmpl.dict())
    db.add(db_tmpl)
    db.commit()
    db.refresh(db_tmpl)
    return db_tmpl


def update_template(
    db: Session, key: str, version: int, patch: schemas.TemplateUpdate
) -> Optional[models.Template]:
    db_tmpl = (
        db.query(models.Template)
        .filter(models.Template.key == key, models.Template.version == version)
        .first()
    )
    if not db_tmpl:
        return None
    update_data = patch.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_tmpl, field, value)
    db.commit()
    db.refresh(db_tmpl)
    return db_tmpl


def get_template(db: Session, key: str, version: int) -> Optional[models.Template]:
    return (
        db.query(models.Template)
        .filter(models.Template.key == key, models.Template.version == version)
        .first()
    )


def get_template_by_key_version(db: Session, key: str, version: int) -> Optional[models.Template]:
    """Alias for compatibility with newer callers."""
    return get_template(db, key=key, version=version)


def list_templates(
    db: Session, active: Optional[bool] = None, skip: int = 0, limit: int = 50
) -> List[models.Template]:
    q = db.query(models.Template)
    if active is not None:
        q = q.filter(models.Template.is_active == active)
    return q.offset(skip).limit(limit).all()


# --- Plans CRUD ---
def create_plan(db: Session, plan: schemas.MatchPlanCreate) -> models.MatchPlan:
    db_plan = models.MatchPlan(**plan.dict())
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    return db_plan


def get_plan(db: Session, plan_id: int) -> Optional[models.MatchPlan]:
    return db.query(models.MatchPlan).filter(models.MatchPlan.id == plan_id).first()


def list_plans(db: Session, skip: int = 0, limit: int = 50) -> List[models.MatchPlan]:
    return db.query(models.MatchPlan).offset(skip).limit(limit).all()


# --- Presentations CRUD ---
def create_presentation(db: Session, p: schemas.PresentationCreate) -> models.Presentation:
    data = p.dict()
    # ensure default outcome/presented_at handled by DB defaults; set explicitly if desired
    db_p = models.Presentation(**data)
    db.add(db_p)
    db.commit()
    db.refresh(db_p)
    return db_p


def decide_presentation(
    db: Session, presentation_id: int, decision: schemas.PresentationDecision
) -> Optional[models.Presentation]:
    db_p = db.query(models.Presentation).filter(models.Presentation.id == presentation_id).first()
    if not db_p:
        return None
    # map decision string to enum member on models.PresentationOutcome
    try:
        enum_member = getattr(models.PresentationOutcome, decision.outcome.upper())
    except AttributeError:
        raise ValueError("invalid outcome")
    db_p.outcome = enum_member
    db_p.decided_at = datetime.utcnow()
    db.commit()
    db.refresh(db_p)
    return db_p


def list_presentations_for_user(
    db: Session,
    user_id: int,
    role: Literal["requester", "candidate"] = "requester",
    skip: int = 0,
    limit: int = 50,
) -> List[models.Presentation]:
    q = db.query(models.Presentation)
    if role == "requester":
        q = q.filter(models.Presentation.requester_id == user_id)
    else:
        q = q.filter(models.Presentation.candidate_id == user_id)
    return q.order_by(models.Presentation.presented_at.desc()).offset(skip).limit(limit).all()


def list_pending_presentations(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.Presentation]:
    """
    Return presentations that are pending and have a rendered_message (i.e. admin needs to deliver these).
    Ordered by oldest presented_at first so admin can process in sequence.
    """
    q = (
        db.query(models.Presentation)
        .filter(
            models.Presentation.outcome == models.PresentationOutcome.PENDING,
            models.Presentation.rendered_message != None,
        )
        .order_by(models.Presentation.presented_at.asc())
    )
    return q.offset(skip).limit(limit).all()


def get_presented_counts(db: Session) -> Dict[int, int]:
    rows = (
        db.query(models.Presentation.requester_id, func.count(models.Presentation.id))
        .group_by(models.Presentation.requester_id)
        .all()
    )
    return {r[0]: r[1] for r in rows}


def get_presented_counts_by_candidate(db: Session) -> Dict[int, int]:
    """candidate_id 기준으로 제안 횟수 집계"""
    rows = (
        db.query(models.Presentation.candidate_id, func.count(models.Presentation.id))
        .group_by(models.Presentation.candidate_id)
        .all()
    )
    return {cid: cnt for cid, cnt in rows}


def get_last_presented_at_by_candidate(db: Session) -> Dict[int, datetime]:
    """candidate_id 별 마지막 presented_at 타임스탬프 조회"""
    rows = (
        db.query(models.Presentation.candidate_id, func.max(models.Presentation.presented_at))
        .group_by(models.Presentation.candidate_id)
        .all()
    )
    return {cid: ts for cid, ts in rows}


def list_recent_presented_candidate_ids(
    db: Session, requester_id: int, since_dt: datetime
) -> set[int]:
    """주어진 requester에게 since_dt 이후에 제안된 candidate_id 집합 반환"""
    rows = (
        db.query(models.Presentation.candidate_id)
        .filter(
            models.Presentation.requester_id == requester_id,
            models.Presentation.presented_at >= since_dt,
        )
        .all()
    )
    return {cid for (cid,) in rows}


def create_presentation_with_rendered(
    db: Session,
    requester_id: int,
    candidate_id: int,
    plan_id: Optional[int],
    template_key: str,
    template_version: int,
    rendered_message: str,
) -> models.Presentation:
    """rendered_message 를 가지고 Presentation 레코드 생성 (outcome=pending)."""
    p = models.Presentation(
        requester_id=requester_id,
        candidate_id=candidate_id,
        plan_id=plan_id,
        template_key=template_key,
        template_version=template_version,
        rendered_message=rendered_message,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p
