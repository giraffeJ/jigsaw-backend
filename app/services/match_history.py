"""매치 히스토리 헬퍼

프리젠테이션/매치 히스토리와 관련된 CRUD 작업을 감싸는 작은 래퍼를 제공합니다.
이 모듈은 매칭 알고리즘 코드(app/services/matching.py)가 직접 DB 쿼리에 의존하지 않도록 분리합니다.
"""

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app import crud


def get_presented_counts(db: Session) -> Dict[int, int]:
    """candidate_id를 키로 하는 제안 횟수 매핑을 반환합니다.

    Returns:
        Dict[int, int]: {candidate_id: presented_count}
    """
    return crud.get_presented_counts_by_candidate(db)


def get_last_presented_at(db: Session) -> Dict[int, Optional[datetime]]:
    """candidate_id를 키로 하는 마지막 제안 시각 매핑을 반환합니다.

    Returns:
        Dict[int, Optional[datetime]]: {candidate_id: 마지막 presented_at datetime 또는 None}
    """
    return crud.get_last_presented_at_by_candidate(db)


def list_recent_presented_to_requester(
    db: Session, requester_id: int, since_dt: datetime
) -> List[int]:
    """주어진 시점(since_dt) 이후로 요청자(requester)에게 제안된 candidate_id 목록을 반환합니다.

    Args:
        requester_id (int): 요청자 사용자 ID.
        since_dt (datetime): 기준 시각.

    Returns:
        List[int]: 제안된 candidate_id의 리스트.
    """
    return crud.list_recent_presented_candidate_ids(
        db, requester_id=requester_id, since_dt=since_dt
    )


def record_presentation(
    db: Session,
    requester_id: int,
    candidate_id: int,
    plan_id: Optional[int] = None,
    template_key: Optional[str] = None,
    rendered_message: Optional[str] = None,
):
    """기존 crud 함수를 사용해 Presentation 레코드를 생성하는 편의 래퍼입니다.

    Args:
        db (Session): SQLAlchemy 세션.
        requester_id (int): 요청자 사용자 ID.
        candidate_id (int): 후보 사용자 ID.
        plan_id (Optional[int]): 연관 플랜 ID(선택).
        template_key (Optional[str]): 사용한 템플릿 키(선택).
        rendered_message (Optional[str]): 렌더링된 메시지(선택).

    Returns:
        models.Presentation: 생성된 Presentation 레코드 (crud 구현에 따름).
    """
    return crud.create_presentation(
        db,
        requester_id=requester_id,
        candidate_id=candidate_id,
        plan_id=plan_id,
        template_key=template_key,
        rendered_message=rendered_message,
    )
