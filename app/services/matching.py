from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app import crud, models
from app.services.user_management import normalize_workplace


def _in_range(v: Optional[int], lo: Optional[int], hi: Optional[int]) -> bool:
    if v is None:
        return False
    if lo is not None and v < lo:
        return False
    if hi is not None and v > hi:
        return False
    return True


def _satisfy_preference(a: models.User, b: models.User) -> Tuple[bool, List[str]]:
    """
    Check whether user 'b' satisfies user 'a' preferences.

    Notes:
    - preferred_age_min/max are birth years. If both provided and min>max, swap them.
    - preferred_smoking / preferred_religion are stored as comma-separated strings in DB (e.g. "비흡연,전자담배").
      This function parses them into sets and checks membership.
    - Workplace same-company determination uses a normalization + substring/token heuristics.
    """
    reasons: List[str] = []
    ok = True

    # 출생연도 (swap if min > max)
    lo = a.preferred_age_min
    hi = a.preferred_age_max
    if lo is not None and hi is not None and lo > hi:
        lo, hi = hi, lo
    if lo is not None or hi is not None:
        if not _in_range(b.birth_year, lo, hi):
            ok = False

    # 거주지 근접성 (부분 문자열 포함 검사)
    if a.residence and b.residence and (a.residence in b.residence or b.residence in a.residence):
        reasons.append("지역 근접")

    # 흡연 선호 (복수 선택 허용: CSV stored in DB)
    pref_smoking_raw = getattr(a, "preferred_smoking", None)
    if pref_smoking_raw:
        # Build allowed set of normalized strings
        if isinstance(pref_smoking_raw, str):
            allowed = {p.strip() for p in pref_smoking_raw.split(",") if p.strip()}
        elif isinstance(pref_smoking_raw, list) or isinstance(pref_smoking_raw, tuple):
            allowed = {str(p).strip() for p in pref_smoking_raw if p}
        else:
            allowed = {str(pref_smoking_raw).strip()}
        b_val = (
            b.smoking_status.value if hasattr(b.smoking_status, "value") else str(b.smoking_status)
        )
        if not any(b_val == a_allowed for a_allowed in allowed):
            ok = False

    # 종교 선호 (복수 선택 허용: CSV)
    pref_religion_raw = getattr(a, "preferred_religion", None)
    if pref_religion_raw:
        if isinstance(pref_religion_raw, str):
            allowed_r = {p.strip() for p in pref_religion_raw.split(",") if p.strip()}
        elif isinstance(pref_religion_raw, list) or isinstance(pref_religion_raw, tuple):
            allowed_r = {str(p).strip() for p in pref_religion_raw if p}
        else:
            allowed_r = {str(pref_religion_raw).strip()}
        b_rel = b.religion.value if hasattr(b.religion, "value") else str(b.religion)
        if not any(b_rel == r for r in allowed_r):
            ok = False

    # 같은 직장 매칭 허용 여부 - use normalization + substring heuristics

    if getattr(a, "workplace_matching", None):
        wm = a.workplace_matching
        wm_val = wm.value if hasattr(wm, "value") else str(wm)
        if wm_val == "같은 직장 불가능" and a.workplace and b.workplace:
            na = normalize_workplace(a.workplace)
            nb = normalize_workplace(b.workplace)
            same = False
            if na and nb:
                if na == nb or na in nb or nb in na:
                    same = True
                else:
                    # token intersection heuristic
                    ta = set(na.split())
                    tb = set(nb.split())
                    if ta & tb:
                        same = True
            if same:
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
