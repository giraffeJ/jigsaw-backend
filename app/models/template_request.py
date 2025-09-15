from typing import Optional

from pydantic import BaseModel


class TemplateCreate(BaseModel):
    desc: Optional[str] = None
    version: str
    content: str

    class Config:
        extra = "forbid"


class TemplateUpdate(BaseModel):
    desc: Optional[str] = None
    version: Optional[str] = None
    content: Optional[str] = None

    class Config:
        extra = "forbid"


__all__ = ["TemplateCreate", "TemplateUpdate"]
