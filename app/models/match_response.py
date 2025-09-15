"""매칭 응답 모델 (Pydantic).

단일 추천 및 벌크 추천 엔드포인트에서 반환하는 응답 모델들을 정의합니다.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class SingleMatchCandidate(BaseModel):
    """단일 후보 항목 모델.

    필드:
        id: 후보 사용자 ID
        nickname: 후보 닉네임
        filled_template: 템플릿을 채워 반환한 문자열
    """

    id: int
    nickname: str
    filled_template: str


class SingleMatchOut(BaseModel):
    """단일 매칭 응답 모델.

    필드:
        user_id: 요청(대상) 사용자 ID (있을 경우)
        nickname: 요청 사용자 닉네임 (있을 경우)
        candidates: 추천 후보 목록
    """

    user_id: Optional[int] = None
    nickname: Optional[str] = None
    candidates: List[SingleMatchCandidate] = Field(default_factory=list)


class BulkMatchCandidate(BaseModel):
    """벌크 매칭의 각 항목 모델.

    필드:
        for_user_id: 대상 사용자 ID
        for_user_nickname: 대상 사용자 닉네임
        recommended_id: 추천된 사용자 ID (없을 수 있음)
        recommended_nickname: 추천된 사용자 닉네임 (없을 수 있음)
        filled_template: 채워진 템플릿 문자열 (없을 수 있음)
    """

    for_user_id: int
    for_user_nickname: str
    recommended_id: Optional[int] = None
    recommended_nickname: Optional[str] = None
    filled_template: Optional[str] = None


class BulkMatchOut(BaseModel):
    """벌크 매칭 응답 모델.

    필드:
        items: BulkMatchCandidate 항목 목록
    """

    items: List[BulkMatchCandidate] = Field(default_factory=list)


__all__ = [
    "SingleMatchCandidate",
    "SingleMatchOut",
    "BulkMatchCandidate",
    "BulkMatchOut",
]
