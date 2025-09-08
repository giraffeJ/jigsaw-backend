from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud, schemas
from app.db import SessionLocal


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


router = APIRouter(prefix="/admin")


@router.post("/templates", response_model=schemas.Template, summary="템플릿 생성")
def create_template(tmpl: schemas.TemplateCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_template(db, tmpl)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/templates", response_model=List[schemas.Template], summary="템플릿 목록 조회")
def list_templates(
    active: Optional[bool] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    return crud.list_templates(db, active=active, skip=skip, limit=limit)


@router.get("/templates/{key}/{version}", response_model=schemas.Template, summary="템플릿 조회")
def get_template(key: str, version: int, db: Session = Depends(get_db)):
    tmpl = crud.get_template(db, key=key, version=version)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tmpl


@router.patch("/templates/{key}/{version}", response_model=schemas.Template, summary="템플릿 수정")
def patch_template(
    key: str, version: int, patch: schemas.TemplateUpdate, db: Session = Depends(get_db)
):
    tmpl = crud.update_template(db, key=key, version=version, patch=patch)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tmpl
