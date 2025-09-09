from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud, schemas
from app.db import SessionLocal

# template rendering (public) will use template_engine
from app.services.template_engine import default_params, render_string


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Admin router (existing)
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


# Public router for rendering previews
public_router = APIRouter()


@public_router.post(
    "/templates/render",
    response_model=schemas.TemplateRenderResponse,
    summary="템플릿 렌더링 미리보기",
)
def render_template(req: schemas.TemplateRenderRequest, db: Session = Depends(get_db)):
    tmpl = crud.get_template_by_key_version(db, req.key, req.version)
    if not tmpl or not tmpl.is_active:
        raise HTTPException(status_code=404, detail="Template not found")
    params = dict(req.params or {})
    if req.requester_id and req.candidate_id:
        r = crud.get_user(db, req.requester_id)
        c = crud.get_user(db, req.candidate_id)
        if not r or not c:
            raise HTTPException(status_code=404, detail="User not found for render")
        params = {**default_params(r, c), **params}
    try:
        content = render_string(tmpl.content, params)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Render error: {e}")
    return schemas.TemplateRenderResponse(content=content)
