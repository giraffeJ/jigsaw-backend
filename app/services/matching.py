from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app import crud, models


def _in_range(v: Optional[int], lo: Optional[int], hi: Optional[int]) -> bool:
    if v is None:
        return False
    if lo is not None and v < lo:
        return False
    if hi is not None and v > hi:
        return False
    return True


def _satisfy_preference(a: models.User, b: models.User) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    ok = True

    # 출생연도(선호 필드가 연도형)
    if a.preferred_age_min is not None or a.preferred_age_max is not None:
        if not _in_range(b.birth_year, a.preferred_age_min, a.preferred_age_max):
            ok = False

    # 거주지 근접성 (부분 문자열 포함 검사)
    if a.residence and b.residence and (a.residence in b.residence or b.residence in a.residence):
        reasons.append("지역 근접")

    # 흡연 선호 (필드가 설정된 경우에만 필터 적용)
    if getattr(a, "preferred_smoking", None):
        # models.SmokingStatus is an enum; compare by value or by raw string
        pref = a.preferred_smoking
        # pref might be enum member or string
        pref_val = pref.value if hasattr(pref, "value") else pref
        b_val = b.smoking_status.value if hasattr(b.smoking_status, "value") else b.smoking_status
        if pref_val and b_val and pref_val != b_val:
            ok = False

    # 종교 선호
    if getattr(a, "preferred_religion", None):
        if (
            a.preferred_religion
            and b.religion
            and a.preferred_religion
            != (b.religion.value if hasattr(b.religion, "value") else b.religion)
        ):
            ok = False

    # 같은 직장 매칭 허용 여부
    if getattr(a, "workplace_matching", None):
        # If marked IMPOSSIBLE and workplaces match (부분 문자열), then disallow
        wm = a.workplace_matching
        wm_val = wm.value if hasattr(wm, "value") else wm
        if (
            wm_val == "같은 직장 불가능"
            and a.workplace
            and b.workplace
            and (a.workplace in b.workplace or b.workplace in a.workplace)
        ):
            ok = False

    return ok, reasons


def mutual_candidates(
    db: Session, requester: models.User, cooldown_days: int, limit: int
) -> List[Dict[str, Any]]:
    # 전체 후보(본인 제외, 활성+동의자)
    pool = crud.get_users_for_matching(db, exclude_user_id=requester.id, skip=0, limit=10_000)

    # 쿨다운: 최근 N일 내 A에게 노출된 candidate_id 집합
    since = datetime.utcnow() - timedelta(days=cooldown_days)
    recent = crud.list_recent_presented_candidate_ids(db, requester_id=requester.id, since_dt=since)

    # 후보별 분포 지표
    presented_cnt = crud.get_presented_counts_by_candidate(db)  # {candidate_id: count}
    last_presented = crud.get_last_presented_at_by_candidate(db)  # {candidate_id: dt}

    out: List[Dict[str, Any]] = []
    for cand in pool:
        if cand.id in recent:
            continue
        ok_ab, r1 = _satisfy_preference(requester, cand)
        ok_ba, r2 = _satisfy_preference(cand, requester)
        if not (ok_ab and ok_ba):
            continue
        score = 0.0
        if "지역 근접" in (r1 + r2):
            score += 0.1
        out.append(
            {
                "candidate_id": cand.id,
                "score": round(score, 3),
                "reasons": list(set(r1 + r2)),
                "presented_count": presented_cnt.get(cand.id, 0),
                "last_presented_at": last_presented.get(cand.id),
            }
        )

    # 정렬: presented_count 오름차순, last_presented_at 오래된 순, score 내림차순
    out.sort(
        key=lambda x: (
            x["presented_count"],
            x["last_presented_at"] or datetime(1970, 1, 1),
            -x["score"],
        )
    )
    return out[:limit]
