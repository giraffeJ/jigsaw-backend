from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

ResultLiteral = Literal["pending", "accepted", "rejected"]


class HistoryCreate(BaseModel):
    """
    생성용 요청 모델
    - to_user_id: 변경(결과를 기록할) 대상의 user id (누구에게)
    - target_user_id: 상대방 user id (누구를)
    - proposal_result / counterpart_result / final_result: 상태 (기본 'pending')
    - *_at: 각 결과가 발생한 시각 (옵셔널)
    """

    to_user_id: int
    target_user_id: int
    proposal_result: ResultLiteral = "pending"
    counterpart_result: ResultLiteral = "pending"
    final_result: ResultLiteral = "pending"
    proposal_result_at: Optional[datetime] = None
    counterpart_result_at: Optional[datetime] = None
    final_result_at: Optional[datetime] = None


class HistoryUpdateById(BaseModel):
    """
    ID(또는 내부에서 사용될 PK 기반) 업데이트용 모델.
    모든 결과 필드는 Optional이며, 지정된 필드만 업데이트하도록 사용합니다.
    """

    proposal_result: Optional[ResultLiteral] = None
    counterpart_result: Optional[ResultLiteral] = None
    final_result: Optional[ResultLiteral] = None
    proposal_result_at: Optional[datetime] = None
    counterpart_result_at: Optional[datetime] = None
    final_result_at: Optional[datetime] = None


class HistoryUpdateByPair(BaseModel):
    """
    (to_user_id, target_user_id) 쌍을 기준으로 업데이트할 때 사용.
    to_user_id / target_user_id 는 필수이며, 나머지 결과 필드는 Optional 입니다.
    """

    to_user_id: int
    target_user_id: int
    proposal_result: Optional[ResultLiteral] = None
    counterpart_result: Optional[ResultLiteral] = None
    final_result: Optional[ResultLiteral] = None
    proposal_result_at: Optional[datetime] = None
    counterpart_result_at: Optional[datetime] = None
    final_result_at: Optional[datetime] = None
