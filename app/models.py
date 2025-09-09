import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from .db import Base


class EducationLevel(enum.Enum):
    HIGH_SCHOOL = "고등학교"
    COLLEGE = "전문대"
    UNIVERSITY = "대학교"
    GRADUATE = "대학원"


class SmokingStatus(enum.Enum):
    SMOKER = "흡연"
    NON_SMOKER = "비흡연"
    OCCASIONAL = "가끔"


class Religion(enum.Enum):
    NONE = "무교"
    CHRISTIAN = "기독교"
    CATHOLIC = "천주교"
    BUDDHIST = "불교"
    OTHER = "기타"


class WorkplaceMatching(enum.Enum):
    POSSIBLE = "같은 직장 가능"
    IMPOSSIBLE = "같은 직장 불가능"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # 기본 정보
    nickname = Column(String(100), nullable=False, comment="카카오톡 오픈채팅방 닉네임")
    referrer_info = Column(Text, nullable=True, comment="추천인 정보 (이름과 관계)")

    # 개인정보 동의
    privacy_consent = Column(
        Boolean, default=False, nullable=False, comment="개인정보 수집 및 제3자 제공 동의"
    )
    confidentiality_consent = Column(
        Boolean, default=False, nullable=False, comment="정보 유출 책임 동의"
    )

    # 본인 확인용 인적사항 (비공개)
    real_name = Column(String(100), nullable=False, comment="실명")
    kakao_id = Column(String(100), nullable=False, comment="카카오톡 ID")
    phone_number = Column(String(20), nullable=False, comment="전화번호")

    # 공개 인적사항
    birth_year = Column(Integer, nullable=False, comment="출생연도")
    height = Column(Integer, nullable=False, comment="키(cm)")
    residence = Column(String(200), nullable=False, comment="거주지 (구 단위)")
    education_level = Column(Enum(EducationLevel), nullable=False, comment="학력")
    final_education = Column(String(200), nullable=False, comment="최종 학력 (학교명)")
    job_title = Column(String(200), nullable=False, comment="직업")
    workplace = Column(Text, nullable=False, comment="직장 (상세)")
    workplace_address = Column(String(200), nullable=False, comment="근무지 주소")
    religion = Column(Enum(Religion), nullable=False, comment="종교")
    smoking_status = Column(Enum(SmokingStatus), nullable=False, comment="흡연 여부")
    mbti = Column(String(4), nullable=True, comment="MBTI")
    hobbies = Column(Text, nullable=True, comment="취미")
    additional_info = Column(Text, nullable=True, comment="기타 (자유 기술)")

    # 매칭 조건
    # preferred_age_range를 정수형(min/max)으로 분리: birth_year와 동일한 형태의 정수값을 저장합니다.
    preferred_age_min = Column(Integer, nullable=True, comment="선호 출생연도 최소값 (예: 1994)")
    preferred_age_max = Column(Integer, nullable=True, comment="선호 출생연도 최대값 (예: 1998)")
    workplace_matching = Column(
        Enum(WorkplaceMatching), nullable=False, comment="같은 직장 매칭 가능 여부"
    )
    preferred_smoking = Column(Enum(SmokingStatus), nullable=False, comment="선호 흡연 여부")
    preferred_religion = Column(String(200), nullable=True, comment="선호 종교")
    additional_matching_condition = Column(Text, nullable=True, comment="개인적인 추가 매칭조건")

    # 시스템 필드
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# Presentation outcome enum
class PresentationOutcome(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), nullable=False, comment="템플릿 식별자")
    version = Column(Integer, nullable=False, default=1, comment="템플릿 버전")
    locale = Column(String(10), nullable=False, default="ko", comment="언어/로케일")
    content = Column(Text, nullable=False, comment="템플릿 내용 (마크업/플레인 텍스트)")
    is_active = Column(Boolean, default=True, nullable=False, comment="활성 여부")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (UniqueConstraint("key", "version", name="uq_template_key_version"),)


class MatchPlan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    created_by = Column(String(100), nullable=False, comment="운영자 식별자")
    notes = Column(Text, nullable=True, comment="플랜 관련 메모")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Presentation(Base):
    __tablename__ = "presentations"

    id = Column(Integer, primary_key=True, index=True)
    requester_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    candidate_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)
    template_key = Column(String(100), nullable=True)
    template_version = Column(Integer, nullable=True)
    rendered_message = Column(Text, nullable=True)
    outcome = Column(
        Enum(PresentationOutcome), nullable=False, server_default=PresentationOutcome.PENDING.name
    )
    presented_at = Column(DateTime(timezone=True), server_default=func.now())
    decided_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "requester_id", "candidate_id", "plan_id", name="uq_present_once_per_plan"
        ),
    )
