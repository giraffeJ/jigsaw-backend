"""
Match history helpers

Provides a small wrapper around CRUD operations that relate to presentation / match history.
This keeps matching algorithm code (app/services/matching.py) decoupled from direct DB queries.
"""

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app import crud


def get_presented_counts(db: Session) -> Dict[int, int]:
    """
    Return a mapping {candidate_id: presented_count}.
    """
    return crud.get_presented_counts_by_candidate(db)


def get_last_presented_at(db: Session) -> Dict[int, Optional[datetime]]:
    """
    Return a mapping {candidate_id: last_presented_at_datetime or None}.
    """
    return crud.get_last_presented_at_by_candidate(db)


def list_recent_presented_to_requester(
    db: Session, requester_id: int, since_dt: datetime
) -> List[int]:
    """
    Return list of candidate_ids that have been presented to the requester since `since_dt`.
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
    """
    Convenience wrapper to create a Presentation record using existing crud function(s).
    """
    return crud.create_presentation(
        db,
        requester_id=requester_id,
        candidate_id=candidate_id,
        plan_id=plan_id,
        template_key=template_key,
        rendered_message=rendered_message,
    )
