from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

ResultLiteral = Literal["pending", "accepted", "rejected"]


class HistoryOut(BaseModel):
    """
    match_history 테이블 컬럼을 그대로 반영한 출력용 모델
    """

    id: int
    to_user_id: int
    target_user_id: int
    proposal_result: ResultLiteral
    proposal_result_at: Optional[datetime] = None
    counterpart_result: ResultLiteral
    counterpart_result_at: Optional[datetime] = None
    final_result: ResultLiteral
    final_result_at: Optional[datetime] = None

    class Config:
        orm_mode = True
