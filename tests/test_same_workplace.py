import os
import time
from pathlib import Path

# Use a test-specific sqlite file to avoid clashing with dev DB
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_app.db")

# Remove existing test DB to start fresh
db_path = Path("./test_app.db")
if db_path.exists():
    try:
        db_path.unlink()
    except Exception:
        pass

from fastapi.testclient import TestClient

# Import app after setting DATABASE_URL so app.db picks it up
import app.main as main

client = TestClient(main.app)


def _user_payload(
    nickname: str,
    kakao_id: str,
    phone: str,
    birth_year: int = 1990,
    residence: str = "서울",
    smoking: str = "비흡연",
    religion: str = "무교",
    workplace: str = "회사",
    workplace_matching: str = "같은 직장 가능",
):
    return {
        "nickname": nickname,
        "referrer_info": None,
        "privacy_consent": True,
        "confidentiality_consent": True,
        "real_name": "테스트",
        "kakao_id": kakao_id,
        "phone_number": phone,
        "birth_year": birth_year,
        "height": 170,
        "residence": residence,
        "education_level": "대학교",
        "final_education": "테스트대학",
        "job_title": "개발자",
        "workplace": workplace,
        "workplace_address": "서울",
        "religion": religion,
        "smoking_status": smoking,
        "mbti": None,
        "hobbies": None,
        "additional_info": None,
        "preferred_age_min": None,
        "preferred_age_max": None,
        "workplace_matching": workplace_matching,
        "preferred_smoking": smoking,
        "preferred_religion": None,
        "additional_matching_condition": None,
    }


def _create_user(payload):
    resp = client.post("/users/", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _get_candidate_ids_for(requester_id, limit=10, cooldown_days=0):
    r = client.get(f"/users/{requester_id}/candidates?limit={limit}&cooldown_days={cooldown_days}")
    assert r.status_code == 200, r.text
    items = r.json().get("items", [])
    return [it["candidate_id"] for it in items]


def test_same_company_exact_and_variants_excluded():
    """
    Requester disallows same-company matching. Create candidates where workplace strings are
    variants of the same company and assert they are excluded.
    """
    # requester: disallow same-company
    alice = _create_user(
        _user_payload(
            "alice",
            "alice_kakao",
            "01000000011",
            workplace="주식회사 ABC 주식회사",
            workplace_matching="같은 직장 불가능",
        )
    )
    a_id = alice["id"]

    # candidate 1: exact "ABC"
    bob = _create_user(_user_payload("bob", "bob_kakao_11", "01000000012", workplace="ABC"))
    b_id = bob["id"]

    # candidate 2: with corp markers "(주)ABC"
    carol = _create_user(
        _user_payload("carol", "carol_kakao_11", "01000000013", workplace="(주) ABC")
    )
    c_id = carol["id"]

    # candidate 3: clearly different
    dave = _create_user(_user_payload("dave", "dave_kakao_11", "01000000014", workplace="다른회사"))
    d_id = dave["id"]

    time.sleep(0.01)

    ids = _get_candidate_ids_for(a_id, limit=10, cooldown_days=0)
    # bob and carol should be excluded; only dave should appear
    assert b_id not in ids, f"Expected bob ({b_id}) excluded for same workplace, got {ids}"
    assert c_id not in ids, f"Expected carol ({c_id}) excluded for same workplace, got {ids}"
    assert (
        d_id in ids
    ), f"Expected different-company candidate dave ({d_id}) to be present, got {ids}"


def test_same_company_token_intersection_excluded():
    """
    Token intersection heuristic should detect shared tokens and exclude candidate.
    """
    # requester: disallow same-company
    alice = _create_user(
        _user_payload(
            "alice2",
            "alice2_kakao",
            "01000000021",
            workplace="ABC Technologies Co.",
            workplace_matching="같은 직장 불가능",
        )
    )
    a_id = alice["id"]

    # candidate: shares token "Technologies" and "ABC"
    bob = _create_user(
        _user_payload("bob2", "bob2_kakao", "01000000022", workplace="Technologies ABC Co.")
    )
    b_id = bob["id"]

    # candidate different
    carol = _create_user(
        _user_payload(
            "carol2", "carol2_kakao", "01000000023", workplace="Completely Different Inc."
        )
    )
    c_id = carol["id"]

    time.sleep(0.01)

    ids = _get_candidate_ids_for(a_id, limit=10, cooldown_days=0)
    assert b_id not in ids, f"Expected bob2 ({b_id}) excluded due to token overlap, got {ids}"
    assert c_id in ids, f"Expected carol2 ({c_id}) present, got {ids}"


def test_same_company_allowed_when_requester_permits():
    """
    If requester allows same-company matching, candidates from the same workplace should be allowed.
    """
    alice = _create_user(
        _user_payload(
            "alice3",
            "alice3_kakao",
            "01000000031",
            workplace="주식회사 XYZ",
            workplace_matching="같은 직장 가능",
        )
    )
    a_id = alice["id"]

    bob = _create_user(_user_payload("bob3", "bob3_kakao", "01000000032", workplace="XYZ"))
    b_id = bob["id"]

    time.sleep(0.01)

    ids = _get_candidate_ids_for(a_id, limit=10, cooldown_days=0)
    assert b_id in ids, f"Expected bob3 ({b_id}) present when same-company allowed, got {ids}"
