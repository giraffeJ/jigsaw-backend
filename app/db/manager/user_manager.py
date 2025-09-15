from typing import Any, Dict, List, Optional, Union

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User as UserModel


def _payload_to_dict(payload: Union[Dict[str, Any], object]) -> Dict[str, Any]:
    """페이로드를 평문 딕셔너리로 변환합니다.

    입력으로 평문 dict 또는 Pydantic 유사 객체(``.dict()`` 사용 가능)를 허용합니다.
    필요시 공개 속성들을 읽어와 폴백합니다.

    Args:
        payload (Union[Dict[str, Any], object]): 입력 페이로드 (dict 또는 모델 유사 객체).

    Returns:
        Dict[str, Any]: create/update 연산에 사용할 필드 딕셔너리.
    """
    if payload is None:
        return {}
    if isinstance(payload, dict):
        return payload
    # Pydantic BaseModel-like
    if hasattr(payload, "dict"):
        try:
            return payload.dict(exclude_unset=True)  # type: ignore[attr-defined]
        except TypeError:
            # some models require no args
            return payload.dict()  # type: ignore[attr-defined]
    # Fallback: pull attributes
    result: Dict[str, Any] = {}
    for k in dir(payload):
        if k.startswith("_"):
            continue
        v = getattr(payload, k)
        # skip callables and modules
        if callable(v):
            continue
        result[k] = v
    return result


def create(db: Session, payload: Union[Dict[str, Any], object]) -> UserModel:
    """데이터베이스에 새 사용자 행을 생성합니다.

    이 함수는 트랜잭션(``db.begin()``) 내부에서 실행됩니다. 성공하면 커밋되고,
    예외 발생 시 트랜잭션은 롤백됩니다.

    Args:
        db (Session): SQLAlchemy 세션.
        payload (Union[Dict[str, Any], object]): 사용자 필드를 가진 dict 또는 Pydantic 유사 객체.

    Returns:
        UserModel: 생성되어 세션에 첨부된 User 인스턴스.

    Raises:
        Exception: DB 작업 중 발생한 예외가 전파됩니다(트랜잭션은 롤백됨).
    """
    data = _payload_to_dict(payload)
    with db.begin():
        user = UserModel(**data)
        db.add(user)
        db.flush()
        db.refresh(user)
        return user


def get_by_id(db: Session, id: int) -> Optional[UserModel]:
    """기본 키로 사용자를 조회합니다.

    Args:
        db (Session): SQLAlchemy 세션.
        id (int): 조회할 사용자의 기본 키.

    Returns:
        Optional[UserModel]: 사용자가 존재하면 해당 인스턴스, 없으면 ``None``.
    """
    stmt = select(UserModel).where(UserModel.id == id)
    return db.execute(stmt).scalars().first()


def get_by_nickname(db: Session, nickname: str) -> Optional[UserModel]:
    """고유한 닉네임으로 사용자를 조회합니다.

    Args:
        db (Session): SQLAlchemy 세션.
        nickname (str): 조회할 닉네임.

    Returns:
        Optional[UserModel]: 사용자가 존재하면 해당 인스턴스, 없으면 ``None``.
    """
    stmt = select(UserModel).where(UserModel.nickname == nickname)
    return db.execute(stmt).scalars().first()


def list(
    db: Session,
    *,
    filters: Optional[Dict[str, Any]] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[UserModel]:
    """간단한 동등 비교 필터와 페이징을 지원하는 사용자 목록을 반환합니다.

    지원되는 필터 키: ``id``, ``nickname``, ``gender``, ``is_active``.
    알려지지 않은 필드 키는 의도적으로 무시됩니다(보수적 동작).

    Args:
        db (Session): SQLAlchemy 세션.
        filters (Optional[Dict[str, Any]]): 동등 필터 매핑(선택).
        skip (int): 페이징 오프셋(건수 스킵).
        limit (int): 반환할 최대 건수.

    Returns:
        List[UserModel]: 필터에 매칭되는 사용자 목록.
    """
    stmt = select(UserModel)
    if filters:
        # Support id or nickname quick queries per acceptance criteria
        if "id" in filters:
            stmt = stmt.where(UserModel.id == int(filters["id"]))
        if "nickname" in filters:
            stmt = stmt.where(UserModel.nickname == str(filters["nickname"]))
        if "gender" in filters:
            stmt = stmt.where(UserModel.gender == str(filters["gender"]))
        if "is_active" in filters:
            val = bool(filters["is_active"])
            stmt = stmt.where(UserModel.is_active == val)
    stmt = stmt.offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


def update(db: Session, id: int, payload: Union[Dict[str, Any], object]) -> UserModel:
    """기존 사용자를 업데이트합니다.

    업데이트는 트랜잭션(``db.begin()``) 내에서 수행됩니다. 모델에 존재하는 속성만 할당됩니다.
    호출자는 payload가 허용된 필드만 포함하도록 보장해야 합니다.

    Args:
        db (Session): SQLAlchemy 세션.
        id (int): 업데이트할 사용자 기본 키.
        payload (Union[Dict[str, Any], object]): 업데이트 필드를 포함한 dict 또는 모델 유사 객체.

    Returns:
        UserModel: 업데이트되어 세션에 첨부된 사용자 인스턴스.

    Raises:
        ValueError: 지정된 ``id``의 사용자가 존재하지 않을 경우 발생합니다.
    """
    data = _payload_to_dict(payload)
    with db.begin():
        user = get_by_id(db, id)
        if user is None:
            raise ValueError(f"User with id={id} not found")
        for k, v in data.items():
            # Only set attributes that exist on the model
            if hasattr(user, k):
                setattr(user, k, v)
        db.add(user)
        db.flush()
        db.refresh(user)
        return user


def delete(db: Session, id: int) -> None:
    """사용자를 ID로 삭제(비교적 영구 삭제)합니다.

    삭제는 트랜잭션(``db.begin()``) 내부에서 수행됩니다.

    Args:
        db (Session): SQLAlchemy 세션.
        id (int): 삭제할 사용자의 기본 키.

    Raises:
        ValueError: 지정된 ``id``의 사용자가 존재하지 않을 경우 발생합니다.
    """
    with db.begin():
        user = get_by_id(db, id)
        if user is None:
            raise ValueError(f"User with id={id} not found")
        db.delete(user)


# --- Candidate search utilities ---


def _csv_to_set(value: Optional[str]) -> Optional[set]:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    parts = [p.strip() for p in value.split(",") if p.strip()]
    return set(parts) if parts else None


def _matches_preference_value(pref_value: Optional[str], actual_value: Optional[str]) -> bool:
    """(CSV 포함) 선호값이 실제 값을 만족하는지 평가합니다.

    Args:
        pref_value (Optional[str]): 단일 값 또는 쉼표로 구분된 허용값 문자열.
        actual_value (Optional[str]): 후보자의 실제 값(문자열 또는 None).

    Returns:
        bool: 실제 값이 선호값과 일치하면 True. 선호값이 None이면 '무선호'로 취급하여 True를 반환합니다.
    """
    if pref_value is None:
        return True
    if actual_value is None:
        return False
    pref_set = _csv_to_set(pref_value)
    if pref_set is None:
        # single scalar
        return pref_value == actual_value
    return actual_value in pref_set


def _mutual_preferences_match(a: UserModel, b: UserModel) -> bool:
    """두 사용자 간 상호 선호 호환 여부를 검사합니다.

    최소한으로 수행하는 검사:
    - preferred_gender
    - preferred_age_min / preferred_age_max(출생연도 범위로 해석)
    - preferred_smoking (CSV 지원)
    - preferred_religion (CSV 지원)

    Args:
        a (UserModel): 요청자 사용자.
        b (UserModel): 후보자 사용자.

    Returns:
        bool: 양쪽의 선호가 서로를 허용하면 True, 아니면 False.
    """
    # Gender preference
    if a.preferred_gender:
        if not (b.gender and b.gender == a.preferred_gender):
            return False
    if b.preferred_gender:
        if not (a.gender and a.gender == b.preferred_gender):
            return False

    # Age preference (birth_year bounds). If preferred bounds are set, require candidate.birth_year within range.
    if a.preferred_age_min is not None:
        if b.birth_year is None or b.birth_year < int(a.preferred_age_min):
            return False
    if a.preferred_age_max is not None:
        if b.birth_year is None or b.birth_year > int(a.preferred_age_max):
            return False
    if b.preferred_age_min is not None:
        if a.birth_year is None or a.birth_year < int(b.preferred_age_min):
            return False
    if b.preferred_age_max is not None:
        if a.birth_year is None or a.birth_year > int(b.preferred_age_max):
            return False

    # Smoking preference (stored as CSV on preferred_smoking, actual smoking_status is Enum -> use its name or value)
    if a.preferred_smoking:
        cand_smoking = getattr(b, "smoking_status", None)
        cand_smoking_str = (
            cand_smoking.name
            if hasattr(cand_smoking, "name")
            else str(cand_smoking) if cand_smoking is not None else None
        )
        if not _matches_preference_value(a.preferred_smoking, cand_smoking_str):
            return False
    if b.preferred_smoking:
        cand_smoking = getattr(a, "smoking_status", None)
        cand_smoking_str = (
            cand_smoking.name
            if hasattr(cand_smoking, "name")
            else str(cand_smoking) if cand_smoking is not None else None
        )
        if not _matches_preference_value(b.preferred_smoking, cand_smoking_str):
            return False

    # Religion preference (CSV)
    if a.preferred_religion:
        cand_religion = getattr(b, "religion", None)
        cand_religion_str = (
            cand_religion.name
            if hasattr(cand_religion, "name")
            else str(cand_religion) if cand_religion is not None else None
        )
        if not _matches_preference_value(a.preferred_religion, cand_religion_str):
            return False
    if b.preferred_religion:
        cand_religion = getattr(a, "religion", None)
        cand_religion_str = (
            cand_religion.name
            if hasattr(cand_religion, "name")
            else str(cand_religion) if cand_religion is not None else None
        )
        if not _matches_preference_value(b.preferred_religion, cand_religion_str):
            return False

    # passed all minimal checks
    return True


def search_candidates(db: Session, *, base_user: UserModel, limit: int = 50) -> List[UserModel]:
    """주어진 사용자에 대한 후보자들을 찾습니다.

    이 함수는 활성 사용자이며 본인이 아닌 사용자로 기본 풀을 구성하고,
    base_user의 gender가 설정된 경우 반대 성별을 우선 필터링합니다.
    이후 :func:`_mutual_preferences_match`를 통해 상호 선호를 적용합니다.
    필요 시 히스토리 매니저를 참조하여 과거 매칭 빈도가 낮은 후보를 우선시할 수 있습니다.

    Args:
        db (Session): SQLAlchemy 세션.
        base_user (UserModel): 후보자를 찾을 대상 사용자.
        limit (int): 반환할 후보자 최대 개수.

    Returns:
        List[UserModel]: 후보자 목록(limit까지), 히스토리 기반 정렬이 가능하면 해당 기준으로 정렬되어 반환됩니다.
    """
    stmt = select(UserModel).where(UserModel.is_active == True)  # noqa: E712
    stmt = stmt.where(UserModel.id != base_user.id)
    if base_user.gender:
        # Prefer opposite gender; this is a simple inequality filter.
        stmt = stmt.where(UserModel.gender != base_user.gender)
    # Fetch a reasonably sized pool and perform preference checks in Python for flexibility
    # (keeps SQL simpler and avoids ORM Enum/string conversion pitfalls).
    pool = db.execute(stmt.limit(1000)).scalars().all()

    # Filter by mutual preferences
    filtered: List[UserModel] = []
    for cand in pool:
        try:
            if _mutual_preferences_match(base_user, cand):
                filtered.append(cand)
        except Exception:
            # If any unexpected data causes check to fail, skip candidate conservatively
            continue

    # Try to leverage history stats if available
    match_scores: Dict[int, int] = {}
    try:
        # import locally to avoid hard dependency; history manager may be missing in tests/environment.
        from app.db.manager import history_manager  # type: ignore
    except Exception:
        history_manager = None

    if history_manager is not None:
        # Try a few candidate function names that the history manager might provide.
        # We default to 0 if a call fails.
        fn_candidates = (
            "get_pair_match_count",
            "get_match_count",
            "get_matches_count",
            "pair_count",
        )
        for cand in filtered:
            count = 0
            for fn_name in fn_candidates:
                fn = getattr(history_manager, fn_name, None)
                if callable(fn):
                    try:
                        # Some implementations may expect (db, requester_id, candidate_id)
                        res = fn(db, base_user.id, cand.id)
                        # If returned a tuple or object with count attribute, try to extract int
                        if isinstance(res, (list, tuple)) and res:
                            maybe = res[0]
                            try:
                                count = int(maybe)
                                break
                            except Exception:
                                pass
                        else:
                            try:
                                count = int(res) if res is not None else 0
                                break
                            except Exception:
                                pass
                    except Exception:
                        # Try alternate call signature fn(requester_id, candidate_id)
                        try:
                            res = fn(base_user.id, cand.id)
                            count = int(res) if res is not None else 0
                            break
                        except Exception:
                            continue
            match_scores[cand.id] = count

    # Sort candidates: prefer lower historical match counts (less previously matched),
    # fall back to id-order to keep deterministic results.
    filtered.sort(key=lambda u: (match_scores.get(u.id, 0), u.id))

    return filtered[:limit]
