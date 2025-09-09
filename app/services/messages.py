"""
Messages / template helpers

Wraps template loading and rendering operations. Keeps template logic isolated from matching algorithm.
"""

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app import crud


def render_template_for_presentation(
    db: Session, template_key: str, template_version: Optional[int], context: Dict[str, Any]
) -> str:
    """
    Load a template (by key/version) and render it using a simple .format mapping.
    This is intentionally lightweight; replace with a full template engine if needed.

    Parameters:
    - db: SQLAlchemy Session
    - template_key: template identifier (string)
    - template_version: optional integer version (if None, latest active is used by crud.get_template)
    - context: dict of values used in str.format

    Returns:
    - rendered string (empty string if template not found)
    """
    tpl = crud.get_template(db, key=template_key, version=template_version)
    if not tpl:
        return ""
    content = tpl.content or ""
    try:
        return content.format(**context)
    except Exception:
        # Fallback: return raw content if formatting fails
        return content


def get_active_templates(db: Session):
    """
    Return list of active templates (delegates to crud).
    """
    return crud.list_active_templates(db)
