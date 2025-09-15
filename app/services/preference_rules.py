"""선호 매칭 규칙

이 모듈은 순수(pure) 함수 하나를 제공합니다:

- is_mutually_compatible(a: User, b: User) -> bool

동작 요약:
- 양쪽 사용자에 대해 `gender`가 필요하며 `a.gender != b.gender`를 강제합니다.
- 각 선호 필드는 해당 필드가 존재할 때만 적용됩니다:
  - preferred_age_min / preferred_age_max: 출생연도가 범위 내에 있어야 합니다(경계 중 하나만 존재해도 적용).
  - preferred_smoking: CSV/list/string 형태로 저장될 수 있으며, 후보자의 smoking_status가 허용 목록에 포함되어야 합니다.
  - preferred_religion: CSV/list/string 형태로 저장될 수 있으며, 후보자의 religion이 허용 목록에 포함되어야 합니다.
  - workplace_matching == "같은 직장 불가능": 양쪽 직장이 존재하고 동일하다고 판단되면 후보는 배제됩니다 (정규화 + 부분문자열/토큰 휴리스틱 사용).
- 이 함수는 순수 함수이며 DB 접근을 하지 않아 단위 테스트가 용이합니다.
"""

from typing import Optional, Set

from app import models
from app.services.user_management import normalize_workplace


def _in_range(v: Optional[int], lo: Optional[int], hi: Optional[int]) -> bool:
    if v is None:
        return False
    if lo is not None and v < lo:
        return False
    if hi is not None and v > hi:
        return False
    return True


def _parse_multi_choice(raw) -> Set[str]:
    """CSV / 리스트 / 튜플 / 스칼라를 정규화된 문자열 집합으로 파싱합니다.

    빈 값(Empty/None)은 빈 집합으로 처리합니다.

    Args:
        raw: 입력값(CSV 문자열 또는 반복형 등).

    Returns:
        Set[str]: 정규화된 문자열 집합.
    """
    if not raw:
        return set()
    if isinstance(raw, str):
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        return set(parts)
    if isinstance(raw, (list, tuple, set)):
        return {str(p).strip() for p in raw if p is not None and str(p).strip()}
    return {str(raw).strip()}


def _value_of(maybe_enum_or_str) -> str:
    if maybe_enum_or_str is None:
        return ""
    return getattr(maybe_enum_or_str, "value", str(maybe_enum_or_str))


def _satisfies_preferences(pref_user: models.User, other: models.User) -> bool:
    """`other`가 `pref_user`의 선호 조건을 만족하면 True를 반환합니다.

    각 선호 항목은 해당 필드가 존재(또는 truthy)할 때만 평가됩니다.

    예:
        - preferred_age_min / preferred_age_max: 출생연도 검사
        - preferred_smoking / preferred_religion: 허용 목록 검사
        - workplace_matching == "같은 직장 불가능": 동일 직장 판정 시 거부
    """
    # Age range: preferred_age_min / preferred_age_max are birth years
    lo = getattr(pref_user, "preferred_age_min", None)
    hi = getattr(pref_user, "preferred_age_max", None)
    if lo is not None and hi is not None and lo > hi:
        lo, hi = hi, lo
    if lo is not None or hi is not None:
        if not _in_range(getattr(other, "birth_year", None), lo, hi):
            return False

    # preferred_smoking: allowlist
    pref_smoking_raw = getattr(pref_user, "preferred_smoking", None)
    allowed_smoking = _parse_multi_choice(pref_smoking_raw)
    if allowed_smoking:
        other_smoking = _value_of(getattr(other, "smoking_status", None))
        if not any(other_smoking == a for a in allowed_smoking):
            return False

    # preferred_religion: allowlist
    pref_religion_raw = getattr(pref_user, "preferred_religion", None)
    allowed_religion = _parse_multi_choice(pref_religion_raw)
    if allowed_religion:
        other_rel = _value_of(getattr(other, "religion", None))
        if not any(other_rel == r for r in allowed_religion):
            return False

    # workplace matching: if user disallows same workplace and both workplaces present,
    # check normalized equality/substring/token intersection -> reject if same.
    wm = getattr(pref_user, "workplace_matching", None)
    if wm:
        wm_val = _value_of(wm)
        if wm_val == "같은 직장 불가능":
            wa = getattr(pref_user, "workplace", None)
            wb = getattr(other, "workplace", None)
            if wa and wb:
                na = normalize_workplace(wa)
                nb = normalize_workplace(wb)
                same = False
                if na and nb:
                    if na == nb or na in nb or nb in na:
                        same = True
                    else:
                        ta = set(na.split())
                        tb = set(nb.split())
                        if ta & tb:
                            same = True
                if same:
                    return False

    # Other preference fields can be added here following the same "apply if present" policy.
    return True


def is_mutually_compatible(a: models.User, b: models.User) -> bool:
    """두 사용자가 상호 호환되는지 판정합니다.

    조건:
    - 양쪽 사용자에 gender가 존재하고 서로 다를 것.
    - `b`가 `a`의 선호를 만족하고 동시에 `a`가 `b`의 선호를 만족할 것.

    이 함수는 순수 함수로 설계되어 입력으로 주어진 사용자 객체만 사용하며
    DB 접근을 수행하지 않습니다.
    """
    if a is None or b is None:
        return False

    aga = getattr(a, "gender", None)
    agb = getattr(b, "gender", None)
    # 성별 필수
    if not aga or not agb:
        return False
    if aga == agb:
        return False

    return _satisfies_preferences(a, b) and _satisfies_preferences(b, a)
