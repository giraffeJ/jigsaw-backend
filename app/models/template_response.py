from typing import Optional

from pydantic import BaseModel


class TemplateOut(BaseModel):
    id: int
    desc: Optional[str] = None
    version: str
    content: str


__all__ = ["TemplateOut"]
