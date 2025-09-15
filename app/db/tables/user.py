"""사용자 테이블 정의(간단한 shim).

이 파일은 `app.models.User`에서 사용되는 컬럼들을 반영하는 독립적인 선언적 매핑을 제공합니다.
애플리케이션의 ORM 모델과 테이블 정의를 분리하여 관리하기 위한 목적입니다.

주의:
- __tablename__ = "user"
- 컬럼 이름은 `app.models.User`와 일치하도록 의도적으로 설계되어 있습니다.
- 이 파일은 단순 테이블 정의용으로만 사용하고, 애플리케이션의 정식 ORM 클래스는 `app/models.py`를 참조하세요.
"""

import enum

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.db import Base


# Minimal enums to keep parity with app.models (string storage via Enum is optional)
class WorkplaceMatchingEnum(enum.Enum):
    POSSIBLE = "같은 직장 가능"
    IMPOSSIBLE = "같은 직장 불가능"


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Public identity
    nickname = Column(String(128), unique=True, index=True, nullable=False)
    gender = Column(String(1), nullable=True, index=True)  # e.g. 'M', 'F', 'O'
    profile_url = Column(Text, nullable=True)

    # Preference fields (match names used in app/models.py)
    preferred_gender = Column(String(16), nullable=True, index=True)
    preferred_age_min = Column(Integer, nullable=True)
    preferred_age_max = Column(Integer, nullable=True)
    preferred_region = Column(String(64), nullable=True, index=True)
    preferred_city = Column(String(64), nullable=True)
    preferred_smoking = Column(String(200), nullable=True)
    preferred_religion = Column(String(200), nullable=True)

    # System fields
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} nickname={self.nickname!r}>"
