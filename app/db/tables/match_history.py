"""매치 히스토리 테이블 정의.

app/db/tables/user.py와 동일한 스타일의 간단한 선언적 테이블 매핑을 제공합니다.
이 파일은 app.models와 동기화된 테이블 정의를 유지하기 위한 용도입니다.
"""

import enum

from sqlalchemy import CheckConstraint, Column, DateTime, Enum, ForeignKey, Integer, text

from app.db import Base


class ProposalResultEnum(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class MatchHistory(Base):
    __tablename__ = "match_history"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # "누구에게" (the recipient / owner of this match record)
    to_user_id = Column(Integer, ForeignKey("user.id"), index=True, nullable=False)

    # "누구를" (the target of the match)
    target_user_id = Column(Integer, ForeignKey("user.id"), index=True, nullable=False)

    # Proposal / responses
    proposal_result = Column(
        Enum(ProposalResultEnum, native_enum=False),
        default=ProposalResultEnum.PENDING,
        server_default=text("'pending'"),
        index=True,
        nullable=False,
    )
    proposal_result_at = Column(DateTime(timezone=True), nullable=True)

    counterpart_result = Column(
        Enum(ProposalResultEnum, native_enum=False),
        default=ProposalResultEnum.PENDING,
        server_default=text("'pending'"),
        index=True,
        nullable=False,
    )
    counterpart_result_at = Column(DateTime(timezone=True), nullable=True)

    final_result = Column(
        Enum(ProposalResultEnum, native_enum=False),
        default=ProposalResultEnum.PENDING,
        server_default=text("'pending'"),
        index=True,
        nullable=False,
    )
    final_result_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # Prevent self-matching
        CheckConstraint("to_user_id != target_user_id", name="chk_match_no_self"),
    )

    def __repr__(self) -> str:
        return (
            f"<MatchHistory id={self.id} to_user_id={self.to_user_id} "
            f"target_user_id={self.target_user_id} final_result={self.final_result}>"
        )
