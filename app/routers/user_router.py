"""사용자 라우터 엔드포인트.

모든 엔드포인트는 Google 스타일 도큐스트링을 사용합니다. 각 핸들러는 인자, 응답 예시,
예외 케이스(4xx/5xx)를 문서화합니다.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.manager import user_manager
from app.models.user_request import UserCreate, UserUpdate
from app.models.user_response import UserOut

router = APIRouter(prefix="/user", tags=["user"])


@router.post("", response_model=UserOut, status_code=201, summary="사용자 생성")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """새 사용자 생성.

    Args:
        user (UserCreate): 사용자 생성에 필요한 페이로드입니다.
        db (Session): Depends(get_db)로 제공되는 데이터베이스 세션입니다.

    Returns:
        UserOut: 생성된 사용자 객체를 반환합니다.

    Raises:
        HTTPException: 검증 실패 시 400 Bad Request를 반환합니다.
            (user_manager.create가 ValueError를 발생시키면 400으로 변환됩니다.)

    Example:
        요청 JSON 예시:
        {
            "nickname": "alice",
            "gender": "F",
            "profile_url": null,
            "preferred_gender": null,
            "preferred_age_min": null,
            "preferred_age_max": null,
            "preferred_region": null,
            "preferred_city": null,
            "preferred_smoking": null,
            "preferred_religion": null,
            "workplace_matching": false,
            "additional_matching_condition": null
        }

    Notes:
        :mod:`app.db.manager.user_manager`를 통해 영속화됩니다.
    """
    try:
        u = user_manager.create(db, user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "id": u.id,
        "nickname": u.nickname,
        "gender": u.gender,
        "profile_url": u.profile_url,
        "preferred_gender": u.preferred_gender,
        "preferred_age_min": u.preferred_age_min,
        "preferred_age_max": u.preferred_age_max,
        "preferred_region": u.preferred_region,
        "preferred_city": u.preferred_city,
        "preferred_smoking": u.preferred_smoking,
        "preferred_religion": u.preferred_religion,
        "workplace_matching": u.workplace_matching,
        "additional_matching_condition": u.additional_matching_condition,
    }


@router.get("", response_model=List[UserOut], summary="사용자 목록 조회")
def list_users(
    nickname: Optional[str] = Query(None, description="닉네임으로 필터"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1),
    db: Session = Depends(get_db),
):
    """닉네임 필터 및 페이징을 지원하는 사용자 목록 조회.

    Args:
        nickname (Optional[str]): 닉네임으로 필터링(선택).
        skip (int): 페이징을 위한 건수 스킵값.
        limit (int): 반환할 최대 레코드 수.
        db (Session): Depends(get_db)로 제공되는 데이터베이스 세션.

    Returns:
        List[UserOut]: 쿼리 결과로 반환되는 사용자 목록.

    Raises:
        HTTPException: FastAPI 유효성 검사에서 잘못된 쿼리 파라미터가 발생할 수 있습니다.

    Example:
        GET /user?nickname=alice&skip=0&limit=10

    Notes:
        내부적으로 :func:`app.db.manager.user_manager.list`를 사용합니다.
    """
    filters = {}
    if nickname is not None:
        filters["nickname"] = nickname
    items = user_manager.list(db, filters=filters if filters else None, skip=skip, limit=limit)
    return [
        {
            "id": u.id,
            "nickname": u.nickname,
            "gender": u.gender,
            "profile_url": u.profile_url,
            "preferred_gender": u.preferred_gender,
            "preferred_age_min": u.preferred_age_min,
            "preferred_age_max": u.preferred_age_max,
            "preferred_region": u.preferred_region,
            "preferred_city": u.preferred_city,
            "preferred_smoking": u.preferred_smoking,
            "preferred_religion": u.preferred_religion,
            "workplace_matching": u.workplace_matching,
            "additional_matching_condition": u.additional_matching_condition,
        }
        for u in items
    ]


@router.get("/{id}", response_model=UserOut, summary="사용자 조회 (id)")
def get_user(id: int, db: Session = Depends(get_db)):
    """기본키 ID로 사용자 조회.

    Args:
        id (int): 조회할 사용자의 기본키 ID.
        db (Session): Depends(get_db)로 제공되는 데이터베이스 세션.

    Returns:
        UserOut: 조회된 사용자 객체.

    Raises:
        HTTPException: 사용자가 존재하지 않으면 404 Not Found를 반환합니다.

    Example:
        GET /user/123

    Notes:
        :func:`app.db.manager.user_manager.get_by_id`를 사용합니다.
    """
    u = user_manager.get_by_id(db, id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": u.id,
        "nickname": u.nickname,
        "gender": u.gender,
        "profile_url": u.profile_url,
        "preferred_gender": u.preferred_gender,
        "preferred_age_min": u.preferred_age_min,
        "preferred_age_max": u.preferred_age_max,
        "preferred_region": u.preferred_region,
        "preferred_city": u.preferred_city,
        "preferred_smoking": u.preferred_smoking,
        "preferred_religion": u.preferred_religion,
        "workplace_matching": u.workplace_matching,
        "additional_matching_condition": u.additional_matching_condition,
    }


@router.get("/by-nickname/{nickname}", response_model=UserOut, summary="사용자 조회 (nickname)")
def get_user_by_nickname(nickname: str, db: Session = Depends(get_db)):
    """닉네임으로 사용자 조회.

    Args:
        nickname (str): 조회할 닉네임.
        db (Session): Depends(get_db)로 제공되는 데이터베이스 세션.

    Returns:
        UserOut: 조회된 사용자 객체.

    Raises:
        HTTPException: 해당 닉네임의 사용자가 없으면 404 Not Found를 반환합니다.

    Example:
        GET /user/by-nickname/alice

    Notes:
        :func:`app.db.manager.user_manager.get_by_nickname`를 사용합니다.
    """
    u = user_manager.get_by_nickname(db, nickname)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": u.id,
        "nickname": u.nickname,
        "gender": u.gender,
        "profile_url": u.profile_url,
        "preferred_gender": u.preferred_gender,
        "preferred_age_min": u.preferred_age_min,
        "preferred_age_max": u.preferred_age_max,
        "preferred_region": u.preferred_region,
        "preferred_city": u.preferred_city,
        "preferred_smoking": u.preferred_smoking,
        "preferred_religion": u.preferred_religion,
        "workplace_matching": u.workplace_matching,
        "additional_matching_condition": u.additional_matching_condition,
    }


@router.patch("/{id}", response_model=UserOut, summary="사용자 수정 (id)")
def patch_user(id: int, patch: UserUpdate, db: Session = Depends(get_db)):
    """허용된 사용자 필드를 업데이트합니다.

    Args:
        id (int): 수정할 사용자의 기본키 ID.
        patch (UserUpdate): 업데이트할 필드들을 포함한 페이로드.
        db (Session): Depends(get_db)로 제공되는 데이터베이스 세션.

    Returns:
        UserOut: 업데이트된 사용자 객체.

    Raises:
        HTTPException: 사용자가 존재하지 않으면 404 Not Found를 반환합니다.
        HTTPException: 매니저에서 발생한 유효성 오류는 400 Bad Request로 전환될 수 있습니다.

    Example:
        PATCH /user/123
        {
            "nickname": "alice_new"
        }

    Notes:
        업데이트 로직은 :func:`app.db.manager.user_manager.update`에 위임합니다.
    """
    try:
        u = user_manager.update(db, id, patch)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": u.id,
        "nickname": u.nickname,
        "gender": u.gender,
        "profile_url": u.profile_url,
        "preferred_gender": u.preferred_gender,
        "preferred_age_min": u.preferred_age_min,
        "preferred_age_max": u.preferred_age_max,
        "preferred_region": u.preferred_region,
        "preferred_city": u.preferred_city,
        "preferred_smoking": u.preferred_smoking,
        "preferred_religion": u.preferred_religion,
        "workplace_matching": u.workplace_matching,
        "additional_matching_condition": u.additional_matching_condition,
    }


@router.delete("/{id}", status_code=204, summary="사용자 삭제 (id)")
def delete_user(id: int, db: Session = Depends(get_db)):
    """ID로 사용자를 삭제합니다.

    Args:
        id (int): 삭제할 사용자의 기본키 ID.
        db (Session): Depends(get_db)로 제공되는 데이터베이스 세션.

    Returns:
        Response: 성공 시 HTTP 204 No Content를 반환합니다.

    Raises:
        HTTPException: 사용자가 존재하지 않으면 404 Not Found를 반환합니다.

    Example:
        DELETE /user/123

    Notes:
        삭제는 :func:`app.db.manager.user_manager.delete`를 사용하며 성공 시 명시적으로 204를 반환합니다.
    """
    try:
        user_manager.delete(db, id)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
