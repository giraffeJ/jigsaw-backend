from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


# Enums for validation
class EducationLevel(str, Enum):
    HIGH_SCHOOL = "고졸"
    JUNIOR_COLLEGE = "초대졸"
    BACHELORS = "대졸"
    MASTERS = "석사"
    DOCTORATE = "박사"
    OTHER = "기타"


class SmokingStatus(str, Enum):
    SMOKER = "흡연"
    NON_SMOKER = "비흡연"
    E_CIGARETTE = "전자담배"


class Religion(str, Enum):
    NONE = "무교"
    CHRISTIAN = "기독교"
    CATHOLIC = "천주교"
    BUDDHIST = "불교"
    OTHER = "기타"


class WorkplaceMatching(str, Enum):
    POSSIBLE = "같은 직장 가능"
    IMPOSSIBLE = "같은 직장 불가능"


# User schemas (새로운 매칭 시스템용)
class UserBase(BaseModel):
    # 기본 정보
    nickname: str = Field(..., description="카카오톡 오픈채팅방 닉네임")
    gender: Optional[str] = Field(None, description="성별 (예: 'M', 'F', 'O')")
    profile_url: Optional[str] = Field("", description="프로필 URL (기본 빈 문자열, 운영자가 입력)")
    referrer_info: Optional[str] = Field(None, description="추천인 정보 (이름과 관계)")

    # 개인정보 동의
    privacy_consent: bool = Field(..., description="개인정보 수집 및 제3자 제공 동의")
    confidentiality_consent: bool = Field(..., description="정보 유출 책임 동의")

    # 본인 확인용 인적사항 (비공개)
    real_name: str = Field(..., description="실명")
    kakao_id: str = Field(..., description="카카오톡 ID")
    phone_number: str = Field(
        ...,
        pattern=r"^(\d{9,11}|0\d{1,2}-\d{3,4}-\d{4})$",
        description="전화번호 (예: 010-1234-5678 또는 숫자만 입력: 1012345678)",
    )

    # 공개 인적사항
    birth_year: int = Field(..., ge=1950, le=2010, description="출생연도")
    height: int = Field(..., ge=140, le=220, description="키(cm)")
    residence: str = Field(..., description="거주지 (구 단위)")
    education_level: Union[EducationLevel, str] = Field(
        ..., description="학력 (예: '대학교' 또는 '대졸' 등 자유 입력 허용)"
    )
    final_education: str = Field(..., description="최종 학력 (학교명)")
    job_title: str = Field(..., description="직업")
    workplace: str = Field(..., description="직장 (상세)")
    workplace_address: str = Field(..., description="근무지 주소")
    religion: Union[Religion, str] = Field(..., description="종교 (Enum 값 또는 자유 입력 허용)")
    smoking_status: Union[SmokingStatus, str] = Field(
        ..., description="흡연 여부 (Enum 값 또는 자유 입력 허용)"
    )
    mbti: Optional[str] = Field(None, description="MBTI")
    hobbies: Optional[str] = Field(None, description="취미")
    additional_info: Optional[str] = Field(None, description="기타 (자유 기술)")

    # 매칭 조건
    # preferred_age_range를 preferred_age_min / preferred_age_max 정수로 분리
    preferred_gender: Optional[str] = Field(None, description="선호 성별 (예: 'M','F','O')")
    preferred_age_min: Optional[int] = Field(
        None, ge=1980, le=2006, description="선호 출생연도 최소값 (4자리, 1980~2006)"
    )
    preferred_age_max: Optional[int] = Field(
        None, ge=1980, le=2006, description="선호 출생연도 최대값 (4자리, 1980~2006)"
    )
    workplace_matching: Union[WorkplaceMatching, str] = Field(
        ..., description="같은 직장 매칭 가능 여부 (Enum 또는 자유 입력 허용)"
    )
    # 복수 선택 허용: 리스트로 입력 가능 (예: ['비흡연', '전자담배'])
    preferred_smoking: Optional[List[Union[SmokingStatus, str]]] = Field(
        None, description="선호 흡연 여부 (복수 선택 가능)"
    )
    # 복수 선택 허용: 리스트로 입력 가능 (예: ['무교','기독교'])
    preferred_religion: Optional[List[Union[Religion, str]]] = Field(
        None, description="선호 종교 (복수 선택 가능)"
    )
    additional_matching_condition: Optional[str] = Field(None, description="개인적인 추가 매칭조건")


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    # 기본 정보
    nickname: Optional[str] = None
    gender: Optional[str] = None
    referrer_info: Optional[str] = None
    profile_url: Optional[str] = None

    # 공개 인적사항 (본인 확인용 정보는 수정 불가)
    height: Optional[int] = Field(None, ge=140, le=220)
    residence: Optional[str] = None
    education_level: Optional[Union[EducationLevel, str]] = None
    final_education: Optional[str] = None
    job_title: Optional[str] = None
    workplace: Optional[str] = None
    workplace_address: Optional[str] = None
    religion: Optional[Union[Religion, str]] = None
    smoking_status: Optional[Union[SmokingStatus, str]] = None
    mbti: Optional[str] = Field(None, description="MBTI")
    hobbies: Optional[str] = None
    additional_info: Optional[str] = None

    # 매칭 조건
    preferred_age_min: Optional[int] = Field(None, ge=1980, le=2006)
    preferred_age_max: Optional[int] = Field(None, ge=1980, le=2006)
    workplace_matching: Optional[Union[WorkplaceMatching, str]] = None
    preferred_smoking: Optional[List[Union[SmokingStatus, str]]] = None
    preferred_religion: Optional[List[Union[Religion, str]]] = None
    additional_matching_condition: Optional[str] = None

    is_active: Optional[bool] = None


class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    class Config:
        from_attributes = True


# --- Templates schemas ---
class TemplateBase(BaseModel):
    key: str
    version: int = 1
    locale: str = "ko"
    content: str
    is_active: bool = True


class TemplateCreate(TemplateBase):
    pass


class TemplateUpdate(BaseModel):
    key: Optional[str] = None
    version: Optional[int] = None
    locale: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None


class Template(TemplateBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- MatchPlan schemas ---
class MatchPlanBase(BaseModel):
    created_by: str
    notes: Optional[str] = None


class MatchPlanCreate(MatchPlanBase):
    pass


class MatchPlan(MatchPlanBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Presentations schemas ---
class PresentationBase(BaseModel):
    requester_id: int
    candidate_id: int
    plan_id: Optional[int] = None
    template_key: Optional[str] = None
    template_version: Optional[int] = None
    rendered_message: Optional[str] = None


class PresentationCreate(PresentationBase):
    pass


class PresentationDecision(BaseModel):
    outcome: Literal["accepted", "declined"]


class Presentation(PresentationBase):
    id: int
    outcome: str = "pending"
    presented_at: datetime
    decided_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# 공개용 유저 정보 (매칭 시 사용, 민감 정보 제외)
class UserPublic(BaseModel):
    id: int
    nickname: str
    gender: Optional[str] = None
    profile_url: Optional[str] = ""
    birth_year: int
    height: int
    residence: str
    education_level: EducationLevel
    final_education: str
    job_title: str
    religion: Religion
    smoking_status: SmokingStatus
    mbti: Optional[str] = None
    hobbies: Optional[str] = None
    additional_info: Optional[str] = None

    class Config:
        from_attributes = True


# --- Matching response schemas (Phase 2) ---
class CandidateProposal(BaseModel):
    candidate_id: int
    score: float = 0.0
    reasons: List[str] = []
    presented_count: int = 0
    last_presented_at: Optional[datetime] = None


class CandidatesResponse(BaseModel):
    items: List[CandidateProposal]


class PlanPreviewItem(BaseModel):
    user_id: int
    proposals: List[CandidateProposal]


class PlanPreview(BaseModel):
    plan_id: int
    items: List[PlanPreviewItem]


# --- Template rendering / present request & responses (Phase 3) ---
class TemplateRenderRequest(BaseModel):
    key: str
    version: int = 1
    requester_id: Optional[int] = None
    candidate_id: Optional[int] = None
    params: Dict[str, Any] = {}


class TemplateRenderResponse(BaseModel):
    content: str


class PresentRequest(BaseModel):
    candidate_id: int
    template_key: str
    template_version: int = 1
    extra_params: Dict[str, Any] = {}


class PresentResponse(BaseModel):
    presentation_id: int
    rendered_message: str
    outcome: str
    presented_at: datetime


class PlanPresentQuery(BaseModel):
    per_user_limit: int = 1
    cooldown_days: int = 30
    template_key: str
    template_version: int = 1
    dry_run: bool = False
    extra_params: Dict[str, Any] = {}
