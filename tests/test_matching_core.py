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
        "workplace": "회사",
        "workplace_address": "서울",
        "religion": religion,
        "smoking_status": smoking,
        "mbti": None,
        "hobbies": None,
        "additional_info": None,
        "preferred_age_min": None,
        "preferred_age_max": None,
        "workplace_matching": "같은 직장 가능",
        "preferred_smoking": smoking,
        "preferred_religion": None,
        "additional_matching_condition": None,
    }


def test_candidates_ordering_and_cooldown_and_plan_preview():
    # create several users:
    # A = requester (alice)
    # B = candidate with high presented_count (bob)
    # C = candidate recently presented to A (carol) -> should be excluded by cooldown
    # D = candidate with low presented_count (dave)
    # plus extra requesters to generate presented_count for B
    resp = client.post("/users/", json=_user_payload("alice", "alice_kakao", "01000000001"))
    assert resp.status_code == 200, resp.text
    alice = resp.json()
    a_id = alice["id"]

    resp = client.post("/users/", json=_user_payload("bob", "bob_kakao", "01000000002"))
    assert resp.status_code == 200, resp.text
    bob = resp.json()
    b_id = bob["id"]

    resp = client.post("/users/", json=_user_payload("carol", "carol_kakao", "01000000003"))
    assert resp.status_code == 200, resp.text
    carol = resp.json()
    c_id = carol["id"]

    resp = client.post("/users/", json=_user_payload("dave", "dave_kakao", "01000000004"))
    assert resp.status_code == 200, resp.text
    dave = resp.json()
    d_id = dave["id"]

    # extra requesters to bump presented_count for bob (B)
    resp = client.post("/users/", json=_user_payload("eric", "eric_kakao", "01000000005"))
    assert resp.status_code == 200, resp.text
    eric = resp.json()
    e_id = eric["id"]

    resp = client.post("/users/", json=_user_payload("frank", "frank_kakao", "01000000006"))
    assert resp.status_code == 200, resp.text
    frank = resp.json()
    f_id = frank["id"]

    # Create presentations so that bob has higher presented_count
    # eric -> bob
    p1 = client.post("/admin/presentations", json={"requester_id": e_id, "candidate_id": b_id})
    assert p1.status_code == 200, p1.text
    # frank -> bob
    p2 = client.post("/admin/presentations", json={"requester_id": f_id, "candidate_id": b_id})
    assert p2.status_code == 200, p2.text
    # dave -> bob (another requester)
    p3 = client.post("/admin/presentations", json={"requester_id": d_id, "candidate_id": b_id})
    assert p3.status_code == 200, p3.text

    # For cooldown: alice was recently presented carol -> should be excluded when alice requests candidates
    pc = client.post("/admin/presentations", json={"requester_id": a_id, "candidate_id": c_id})
    assert pc.status_code == 200, pc.text

    # small sleep to ensure timestamps if necessary
    time.sleep(0.01)

    # Now request candidates for alice with cooldown_days=30; carol should be excluded.
    r = client.get(f"/users/{a_id}/candidates?limit=10&cooldown_days=30")
    assert r.status_code == 200, r.text
    data = r.json()
    items = data["items"]

    # Ensure carol (c_id) not present due to cooldown
    ids = [it["candidate_id"] for it in items]
    assert c_id not in ids

    # bob has higher presented_count (3) while dave has 0 => dave should come before bob
    # find positions if present
    if d_id in ids and b_id in ids:
        assert ids.index(d_id) < ids.index(b_id)
    else:
        # If one of them is missing, that's an unexpected failure
        assert False, f"expected both candidates present in result ids={ids}"

    # Create a plan and call plan preview endpoint
    p = client.post("/admin/plans", json={"created_by": "tester", "notes": "preview"})
    assert p.status_code == 200, p.text
    plan = p.json()
    plan_id = plan["id"]

    pv = client.post(f"/admin/match/plans/{plan_id}/fill?per_user_limit=1&cooldown_days=30")
    assert pv.status_code == 200, pv.text
    preview = pv.json()
    assert preview["plan_id"] == plan_id
    assert isinstance(preview["items"], list)
    # there should be at least as many preview items as users we created
    assert len(preview["items"]) >= 6
