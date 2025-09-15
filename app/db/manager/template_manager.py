from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.tables.template import Template as TemplateTable


def create(db: Session, *, desc: Optional[str], version: str, content: str) -> TemplateTable:
    """템플릿 행을 생성합니다.

    이 함수는 트랜잭션(``db.begin()``) 내에서 실행됩니다. 성공 시 커밋하고,
    예외 발생 시 트랜잭션은 롤백됩니다.

    Args:
        db (Session): SQLAlchemy 세션.
        desc (Optional[str]): 템플릿 설명(선택).
        version (str): 템플릿 버전 식별자.
        content (str): 템플릿 본문 문자열.

    Returns:
        TemplateTable: 세션에 첨부된 생성된 Template 인스턴스.

    Notes:
        반환값에 id가 할당되도록 세션을 flush한 뒤 리프레시합니다.
    """
    # Using session.begin() guarantees commit on success and rollback on exception.
    with db.begin():
        tpl = TemplateTable(desc=desc, version=str(version), content=content)
        db.add(tpl)
        # flush so id is assigned before returning
        db.flush()
        db.refresh(tpl)
        return tpl


def get_by_id(db: Session, id: int) -> Optional[TemplateTable]:
    """기본키로 템플릿을 조회합니다.

    Args:
        db (Session): SQLAlchemy 세션.
        id (int): 템플릿의 기본키 ID.

    Returns:
        Optional[TemplateTable]: 템플릿이 존재하면 해당 인스턴스, 없으면 ``None``.

    Notes:
        읽기 전용 작업으로 명시적 트랜잭션을 열지 않습니다.
    """
    stmt = select(TemplateTable).where(TemplateTable.id == id)
    return db.execute(stmt).scalars().first()


def list(
    db: Session, *, version: Optional[str] = None, skip: int = 0, limit: int = 50
) -> List[TemplateTable]:
    """버전 필터 및 페이지네이션을 지원하는 템플릿 목록을 반환합니다.

    Args:
        db (Session): SQLAlchemy 세션.
        version (Optional[str]): 필터할 버전(선택).
        skip (int): 페이징 오프셋(스킵할 행 수).
        limit (int): 반환할 최대 행 수.

    Returns:
        List[TemplateTable]: 쿼리에 매칭되는 템플릿 목록.
    """
    stmt = select(TemplateTable)
    if version is not None:
        stmt = stmt.where(TemplateTable.version == str(version))
    stmt = stmt.offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


def update(
    db: Session,
    id: int,
    *,
    desc: Optional[str] = None,
    version: Optional[str] = None,
    content: Optional[str] = None,
) -> TemplateTable:
    """템플릿 필드를 업데이트합니다.

    업데이트는 트랜잭션(``db.begin()``) 내에서 수행되며, 제공된 필드만 갱신됩니다.

    Args:
        db (Session): SQLAlchemy 세션.
        id (int): 업데이트할 템플릿의 기본키 ID.
        desc (Optional[str]): 새로운 설명(선택).
        version (Optional[str]): 새로운 버전(선택).
        content (Optional[str]): 새로운 내용(선택).

    Returns:
        TemplateTable: 갱신된 템플릿 인스턴스.

    Raises:
        ValueError: 지정된 ID의 템플릿이 존재하지 않으면 발생합니다.
    """
    with db.begin():
        tpl = get_by_id(db, id)
        if tpl is None:
            raise ValueError(f"Template with id={id} not found")
        if desc is not None:
            tpl.desc = desc
        if version is not None:
            tpl.version = str(version)
        if content is not None:
            tpl.content = content
        db.add(tpl)
        db.flush()
        db.refresh(tpl)
        return tpl


def delete(db: Session, id: int) -> None:
    """ID로 템플릿을 삭제합니다.

    Args:
        db (Session): SQLAlchemy 세션.
        id (int): 삭제할 템플릿의 기본키 ID.

    Raises:
        ValueError: 지정된 ID의 템플릿이 존재하지 않으면 발생합니다.
    """
    with db.begin():
        tpl = get_by_id(db, id)
        if tpl is None:
            raise ValueError(f"Template with id={id} not found")
        db.delete(tpl)
