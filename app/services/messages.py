"""메시지 및 템플릿 헬퍼

템플릿 로딩 및 렌더링 작업을 감쌉니다. 매칭 알고리즘과 템플릿 로직을 분리하여 유지합니다.
"""

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app import crud


def render_template_for_presentation(
    db: Session, template_key: str, template_version: Optional[int], context: Dict[str, Any]
) -> str:
    """템플릿을 로드하고 간단한 .format 매핑으로 렌더링합니다.

    이 함수는 의도적으로 가볍게 설계되었습니다. 필요시 전체 템플릿 엔진으로 교체하세요.

    Args:
        db (Session): SQLAlchemy 세션.
        template_key (str): 템플릿 식별자.
        template_version (Optional[int]): 템플릿 버전(없을 경우 crud.get_template가 최신 활성 템플릿을 사용).
        context (Dict[str, Any]): str.format에 전달되는 값들의 딕셔너리.

    Returns:
        str: 렌더링된 문자열 (템플릿을 찾지 못하면 빈 문자열을 반환).
    """
    tpl = crud.get_template(db, key=template_key, version=template_version)
    if not tpl:
        return ""
    content = tpl.content or ""
    try:
        return content.format(**context)
    except Exception:
        # 폴백: 포맷팅 실패 시 원본 콘텐츠를 그대로 반환
        return content


def get_active_templates(db: Session):
    """활성 템플릿 목록을 반환합니다 (crud에 위임)."""
    return crud.list_active_templates(db)
