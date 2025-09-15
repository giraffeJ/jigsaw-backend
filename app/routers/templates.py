from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.manager import template_manager
from app.models.template_request import TemplateCreate, TemplateUpdate
from app.models.template_response import TemplateOut

router = APIRouter(prefix="/template", tags=["template"])


@router.post("", response_model=TemplateOut, status_code=201, summary="템플릿 생성")
def create_template(tmpl: TemplateCreate, db: Session = Depends(get_db)):
    """템플릿을 생성합니다.

    설명:
        TemplateManager를 통해 새 템플릿을 생성합니다.
        허용되는 입력 필드: desc, version, content (id는 DB에서 할당됨).
    """
    try:
        tpl = template_manager.create(
            db, desc=tmpl.desc, version=tmpl.version, content=tmpl.content
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": tpl.id, "desc": tpl.desc, "version": str(tpl.version), "content": tpl.content}


@router.get("", response_model=List[TemplateOut], summary="템플릿 목록 조회")
def list_templates(
    version: Optional[int] = Query(None, description="버전 필터 (정수)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1),
    db: Session = Depends(get_db),
):
    """템플릿 목록 조회.

    설명:
        버전 필터 및 페이지네이션(skip/limit)을 지원합니다.
        내부적으로 TemplateManager.list를 사용합니다.
    """
    v = str(version) if version is not None else None
    items = template_manager.list(db, version=v, skip=skip, limit=limit)
    return [{"id": t.id, "desc": t.desc, "version": t.version, "content": t.content} for t in items]


@router.get("/{id}", response_model=TemplateOut, summary="템플릿 조회 (id)")
def get_template(id: int, db: Session = Depends(get_db)):
    """기본키 ID로 템플릿을 조회합니다.

    설명:
        TemplateManager를 통해 id에 해당하는 템플릿을 검색합니다.
        존재하지 않으면 404 응답을 반환합니다.
    """
    tpl = template_manager.get_by_id(db, id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"id": tpl.id, "desc": tpl.desc, "version": tpl.version, "content": tpl.content}


@router.patch("/{id}", response_model=TemplateOut, summary="템플릿 수정 (id)")
def patch_template(id: int, patch: TemplateUpdate, db: Session = Depends(get_db)):
    """템플릿의 허용된 필드(desc, version, content)를 업데이트합니다.

    설명:
        요청 모델에서 허용하지 않는 필드는 적용되지 않습니다.
        존재하지 않는 템플릿 ID에 대해서는 404를 반환합니다.
    """
    try:
        tpl = template_manager.update(
            db,
            id,
            desc=patch.desc,
            version=patch.version,
            content=patch.content,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"id": tpl.id, "desc": tpl.desc, "version": tpl.version, "content": tpl.content}


@router.delete("/{id}", status_code=204, summary="템플릿 삭제 (id)")
def delete_template(id: int, db: Session = Depends(get_db)):
    """ID로 템플릿을 삭제합니다.

    설명:
        TemplateManager를 사용해 템플릿을 삭제합니다.
        성공 시 HTTP 204 No Content를 반환합니다. 템플릿이 없으면 404를 반환합니다.
    """
    try:
        template_manager.delete(db, id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Template not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
