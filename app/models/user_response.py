"""사용자 응답 모델 (Pydantic).

출력용 모델로서 API 응답에 사용되는 필드를 정의합니다.
"""

from typing import Optional

from pydantic import BaseModel


class UserOut(BaseModel):
    """사용자 출력 모델.

    필드:
        id: 사용자 기본키
        nickname: 닉네임
        gender: 성별 코드("M"/"F")
        profile_url: 공개 프로필 URL
    """

    id: int
    nickname: str
    gender: str
    profile_url: str

    # Preference / matching fields
    preferred_gender: Optional[str] = None
    preferred_age_min: Optional[int] = None
    preferred_age_max: Optional[int] = None
    preferred_region: Optional[str] = None
    preferred_city: Optional[str] = None
    preferred_smoking: Optional[str] = None
    preferred_religion: Optional[str] = None
    workplace_matching: Optional[str] = None
    additional_matching_condition: Optional[str] = None


__all__ = ["UserOut"]
