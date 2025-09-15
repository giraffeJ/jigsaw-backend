import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# 기존 환경변수 사용 (없으면 로컬 sqlite 사용)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# SQLite인 경우에는 check_same_thread 옵션이 필요합니다.
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
        future=True,
    )
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

# SQLAlchemy 2.x 스타일 session factory
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


# Declarative base (SQLAlchemy 2.x)
class Base(DeclarativeBase):
    pass


# Dependency for FastAPI / other layers
def get_db() -> Generator[Session, None, None]:
    """데이터베이스 세션을 제공하고 사용 후 닫히도록 보장합니다.

    사용 예제 (FastAPI):
        from app.db import get_db
        def endpoint(db: Session = Depends(get_db)):
            ...

    Returns:
        Generator[Session, None, None]: 데이터베이스 세션 제너레이터.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Exports for easier imports in other layers
__all__ = ["DATABASE_URL", "engine", "SessionLocal", "Base", "get_db"]
