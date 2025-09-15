"""사용자 요청 모델 (Pydantic).

이 파일은 사용자 생성/수정 요청에 사용되는 Pydantic 모델을 정의합니다:
- UserCreate: 사용자 생성에 필요한 필수/선택 필드
- UserUpdate: 부분 업데이트용(Optional 필드)

선호(preference) 관련 필드는 create시 선택적으로 제공될 수 있으며,
DB에는 일부 필드가 CSV 문자열로 저장되는 경우가 있습니다.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


class UserCreate(BaseModel):
    nickname: str
    gender: Literal["M", "F"]
    profile_url: HttpUrl | str = Field(..., description="Public profile URL")

    # Preference / matching fields (optional on create)
    preferred_gender: Optional[str] = None
    preferred_age_min: Optional[int] = None
    preferred_age_max: Optional[int] = None
    preferred_region: Optional[str] = None
    preferred_city: Optional[str] = None
    preferred_smoking: Optional[str] = None
    preferred_religion: Optional[str] = None
    workplace_matching: Optional[str] = None
    additional_matching_condition: Optional[str] = None


class UserUpdate(BaseModel):
    # All fields optional for partial updates
    nickname: Optional[str] = None
    gender: Optional[Literal["M", "F"]] = None
    profile_url: Optional[HttpUrl | str] = None

    preferred_gender: Optional[str] = None
    preferred_age_min: Optional[int] = None
    preferred_age_max: Optional[int] = None
    preferred_region: Optional[str] = None
    preferred_city: Optional[str] = None
    preferred_smoking: Optional[str] = None
    preferred_religion: Optional[str] = None
    workplace_matching: Optional[str] = None
    additional_matching_condition: Optional[str] = None


__all__ = ["UserCreate", "UserUpdate"]
