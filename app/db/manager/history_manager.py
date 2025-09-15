from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.tables.match_history import MatchHistory as MatchHistoryModel, ProposalResultEnum


def _ensure_enum(val: Optional[Any]) -> Optional[ProposalResultEnum]:
    """입력을 가능하면 ProposalResultEnum으로 정규화합니다.

    None, ProposalResultEnum 멤버 또는 'pending'/'accepted'/'rejected' 같은 문자열(대소문자/이름 허용)을 받습니다.
    파싱에 실패하면 ``None``을 반환합니다.

    Args:
        val (Optional[Any]): 정규화할 입력값.

    Returns:
        Optional[ProposalResultEnum]: 대응하는 enum 또는 ``None``.
    """
    if val is None:
        return None
    if isinstance(val, ProposalResultEnum):
        return val
    try:
        return ProposalResultEnum(val)
    except Exception:
        # Try uppercase name (in case caller passed 'PENDING' etc.)
        try:
            return ProposalResultEnum[val]  # type: ignore[index]
        except Exception:
            return None


def create(
    db: Session,
    *,
    to_user_id: int,
    target_user_id: int,
    proposal_result: Any = "pending",
    counterpart_result: Any = "pending",
    final_result: Any = "pending",
    timestamps: Optional[Dict[str, Any]] = None,
) -> MatchHistoryModel:
    """매치 히스토리(MatchHistory) 레코드를 생성합니다.

    result 필드에는 enum 멤버 또는 문자열을 허용합니다. 선택적 ``timestamps`` 딕셔너리는
    ``proposal_result_at``, ``counterpart_result_at``, ``final_result_at`` 키를 포함할 수 있습니다.

    Args:
        db (Session): SQLAlchemy 세션.
        to_user_id (int): 제안을 보낸(또는 기록 대상) 사용자 ID.
        target_user_id (int): 대상 사용자 ID.
        proposal_result (Any): 제안 결과(enum 또는 문자열). 기본값 "pending".
        counterpart_result (Any): 상대 결과(enum 또는 문자열). 기본값 "pending".
        final_result (Any): 최종 결과(enum 또는 문자열). 기본값 "pending".
        timestamps (Optional[Dict[str, Any]]): 결과 이벤트에 대한 선택적 타임스탬프.

    Returns:
        MatchHistoryModel: 생성된 MatchHistory 인스턴스.

    Notes:
        트랜잭션(``db.begin()``) 내에서 실행되며 성공 시 커밋, 오류 시 롤백됩니다.
    """
    ts = timestamps or {}
    pr = _ensure_enum(proposal_result) or ProposalResultEnum.PENDING
    cr = _ensure_enum(counterpart_result) or ProposalResultEnum.PENDING
    fr = _ensure_enum(final_result) or ProposalResultEnum.PENDING

    with db.begin():
        mh = MatchHistoryModel(
            to_user_id=to_user_id,
            target_user_id=target_user_id,
            proposal_result=pr,
            proposal_result_at=ts.get("proposal_result_at"),
            counterpart_result=cr,
            counterpart_result_at=ts.get("counterpart_result_at"),
            final_result=fr,
            final_result_at=ts.get("final_result_at"),
        )
        db.add(mh)
        db.flush()
        db.refresh(mh)
        return mh


def get_by_id(db: Session, id: int) -> Optional[MatchHistoryModel]:
    """기본키로 MatchHistory 레코드를 조회합니다.

    Args:
        db (Session): SQLAlchemy 세션.
        id (int): 조회할 MatchHistory 기본키.

    Returns:
        Optional[MatchHistoryModel]: 존재하면 레코드, 없으면 ``None``.
    """
    return db.query(MatchHistoryModel).filter(MatchHistoryModel.id == id).first()


def list_all(db: Session, *, skip: int = 0, limit: int = 50) -> List[MatchHistoryModel]:
    """모든 MatchHistory 레코드를 페이지네이션하여 반환합니다.

    Args:
        db (Session): SQLAlchemy 세션.
        skip (int): 페이지 오프셋.
        limit (int): 반환 최대 개수.

    Returns:
        List[MatchHistoryModel]: 페이지네이션된 MatchHistory 목록.
    """
    q = db.query(MatchHistoryModel).order_by(MatchHistoryModel.id.asc())
    return q.offset(skip).limit(limit).all()


def list_by_to_user(
    db: Session, to_user_id: int, *, skip: int = 0, limit: int = 50
) -> List[MatchHistoryModel]:
    """주어진 사용자가 'to_user'인 MatchHistory 레코드를 반환합니다.

    Args:
        db (Session): SQLAlchemy 세션.
        to_user_id (int): 필터 대상 to_user_id.
        skip (int): 페이징 오프셋.
        limit (int): 반환 최대 개수.

    Returns:
        List[MatchHistoryModel]: id 오름차순으로 정렬된 매칭 히스토리 행 목록.
    """
    q = db.query(MatchHistoryModel).filter(MatchHistoryModel.to_user_id == to_user_id)
    q = q.order_by(MatchHistoryModel.id.asc())
    return q.offset(skip).limit(limit).all()


def list_by_target_user(
    db: Session, target_user_id: int, *, skip: int = 0, limit: int = 50
) -> List[MatchHistoryModel]:
    """주어진 사용자가 'target_user'인 MatchHistory 레코드를 반환합니다.

    Args:
        db (Session): SQLAlchemy 세션.
        target_user_id (int): 필터 대상 target_user_id.
        skip (int): 페이징 오프셋.
        limit (int): 반환 최대 개수.

    Returns:
        List[MatchHistoryModel]: id 오름차순으로 정렬된 매칭 히스토리 행 목록.
    """
    q = db.query(MatchHistoryModel).filter(MatchHistoryModel.target_user_id == target_user_id)
    q = q.order_by(MatchHistoryModel.id.asc())
    return q.offset(skip).limit(limit).all()


def list_by_status(
    db: Session,
    *,
    proposal: Optional[Any] = None,
    counterpart: Optional[Any] = None,
    final: Optional[Any] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[MatchHistoryModel]:
    """결과 필드(proposal/counterpart/final)를 기준으로 매치 히스토리를 필터링합니다.

    proposal, counterpart, final 각 필드에 대해 enum 멤버 또는 문자열을 전달하면
    해당 상태로 필터링합니다. None을 전달하면 해당 필드 필터링을 건너뜁니다.

    Args:
        db (Session): SQLAlchemy 세션.
        proposal (Optional[Any]): proposal 결과 필터(enum 또는 문자열).
        counterpart (Optional[Any]): counterpart 결과 필터(enum 또는 문자열).
        final (Optional[Any]): final 결과 필터(enum 또는 문자열).
        skip (int): 페이징 오프셋.
        limit (int): 반환 최대 개수.

    Returns:
        List[MatchHistoryModel]: id 오름차순으로 정렬된 매칭 히스토리 행 목록.
    """
    q = db.query(MatchHistoryModel)
    if proposal is not None:
        pr = _ensure_enum(proposal)
        if pr is not None:
            q = q.filter(MatchHistoryModel.proposal_result == pr)
        else:
            # If unable to parse, filter by raw value (defensive)
            q = q.filter(MatchHistoryModel.proposal_result == proposal)
    if counterpart is not None:
        cr = _ensure_enum(counterpart)
        if cr is not None:
            q = q.filter(MatchHistoryModel.counterpart_result == cr)
        else:
            q = q.filter(MatchHistoryModel.counterpart_result == counterpart)
    if final is not None:
        fr = _ensure_enum(final)
        if fr is not None:
            q = q.filter(MatchHistoryModel.final_result == fr)
        else:
            q = q.filter(MatchHistoryModel.final_result == final)
    q = q.order_by(MatchHistoryModel.id.asc())
    return q.offset(skip).limit(limit).all()


def update_results(
    db: Session,
    id: int,
    *,
    proposal_result: Optional[Any] = None,
    counterpart_result: Optional[Any] = None,
    final_result: Optional[Any] = None,
    proposal_result_at: Optional[Any] = None,
    counterpart_result_at: Optional[Any] = None,
    final_result_at: Optional[Any] = None,
) -> MatchHistoryModel:
    """MatchHistory 행의 결과 필드를 업데이트합니다.

    결과 필드를 제공했으나 해당 타임스탬프가 제공되지 않은 경우, 현재 UTC 시각으로 설정합니다.

    Args:
        db (Session): SQLAlchemy 세션.
        id (int): 업데이트할 MatchHistory 기본키.
        proposal_result (Optional[Any]): 새로운 proposal 결과(enum 또는 문자열).
        counterpart_result (Optional[Any]): 새로운 counterpart 결과(enum 또는 문자열).
        final_result (Optional[Any]): 새로운 final 결과(enum 또는 문자열).
        proposal_result_at (Optional[Any]): proposal 결과의 명시적 타임스탬프.
        counterpart_result_at (Optional[Any]): counterpart 결과의 명시적 타임스탬프.
        final_result_at (Optional[Any]): final 결과의 명시적 타임스탬프.

    Returns:
        MatchHistoryModel: 업데이트된 MatchHistory 인스턴스.

    Raises:
        ValueError: 지정된 id의 MatchHistory가 존재하지 않을 경우 발생합니다.
    """
    with db.begin():
        mh = get_by_id(db, id)
        if mh is None:
            raise ValueError(f"MatchHistory with id={id} not found")

        now = datetime.utcnow()

        if proposal_result is not None:
            mh.proposal_result = _ensure_enum(proposal_result) or ProposalResultEnum.PENDING
            mh.proposal_result_at = proposal_result_at or now

        if counterpart_result is not None:
            mh.counterpart_result = _ensure_enum(counterpart_result) or ProposalResultEnum.PENDING
            mh.counterpart_result_at = counterpart_result_at or now

        if final_result is not None:
            mh.final_result = _ensure_enum(final_result) or ProposalResultEnum.PENDING
            mh.final_result_at = final_result_at or now

        db.add(mh)
        db.flush()
        db.refresh(mh)
        return mh


def delete(db: Session, id: int) -> None:
    """ID로 MatchHistory 행을 삭제합니다.

    Args:
        db (Session): SQLAlchemy 세션.
        id (int): 삭제할 MatchHistory 기본키.

    Raises:
        ValueError: 지정된 id의 MatchHistory가 존재하지 않을 경우 발생합니다.
    """
    with db.begin():
        mh = get_by_id(db, id)
        if mh is None:
            raise ValueError(f"MatchHistory with id={id} not found")
        db.delete(mh)


# Additional helpers used by other parts of the codebase (optional but convenient)


def stats_match_counts(db: Session, user_id: int) -> Tuple[int, int]:
    """사용자에 대한 매치 카운트를 반환합니다.

    반환값은 ``(as_to_user_count, as_target_user_count)`` 형태로,
    해당 사용자가 to_user로 등장한 횟수와 target_user로 등장한 횟수를 나타냅니다.

    Args:
        db (Session): SQLAlchemy 세션.
        user_id (int): 통계를 계산할 사용자 ID.

    Returns:
        Tuple[int, int]: (as_to_user_count, as_target_user_count) 카운트.
    """
    as_to = (
        db.query(func.count(MatchHistoryModel.id))
        .filter(MatchHistoryModel.to_user_id == user_id)
        .scalar()
        or 0
    )
    as_target = (
        db.query(func.count(MatchHistoryModel.id))
        .filter(MatchHistoryModel.target_user_id == user_id)
        .scalar()
        or 0
    )
    return (int(as_to), int(as_target))


def get_pair_match_count(db: Session, user_a_id: int, user_b_id: int) -> int:
    """두 사용자 간의 매치 레코드 수를 반환합니다 (양 방향 모두 포함).

    Args:
        db (Session): SQLAlchemy 세션.
        user_a_id (int): 첫 번째 사용자 ID.
        user_b_id (int): 두 번째 사용자 ID.

    Returns:
        int: 두 사용자 간의 매치 레코드 수.
    """
    cnt = (
        db.query(func.count(MatchHistoryModel.id))
        .filter(
            or_(
                (MatchHistoryModel.to_user_id == user_a_id)
                & (MatchHistoryModel.target_user_id == user_b_id),
                (MatchHistoryModel.to_user_id == user_b_id)
                & (MatchHistoryModel.target_user_id == user_a_id),
            )
        )
        .scalar()
    ) or 0
    return int(cnt)
