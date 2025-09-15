from sqlalchemy import Column, Integer, String, Text

from app.db import Base


class Template(Base):
    __tablename__ = "template"

    id = Column(Integer, primary_key=True, autoincrement=True)
    desc = Column(Text, nullable=True)
    version = Column(String(32), nullable=False, index=True)
    content = Column(Text, nullable=False)

    def __repr__(self) -> str:
        return f"<Template id={self.id} version={self.version!r}>"
