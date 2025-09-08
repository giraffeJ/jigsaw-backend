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


def _user_payload(nickname: str, kakao_id: str, phone: str):
    return {
        "nickname": nickname,
        "referrer_info": None,
        "privacy_consent": True,
        "confidentiality_consent": True,
        "real_name": "테스트",
        "kakao_id": kakao_id,
        "phone_number": phone,
        "birth_year": 1990,
        "height": 170,
        "residence": "서울",
        "education_level": "대학교",
        "final_education": "테스트대학",
        "job_title": "개발자",
        "workplace": "회사",
        "workplace_address": "서울",
        "religion": "무교",
        "smoking_status": "비흡연",
        "mbti": None,
        "hobbies": None,
        "additional_info": None,
        "preferred_age_min": None,
        "preferred_age_max": None,
        "workplace_matching": "같은 직장 가능",
        "preferred_smoking": "비흡연",
        "preferred_religion": None,
        "additional_matching_condition": None,
    }


def test_template_create_and_get():
    # Create template
    resp = client.post(
        "/admin/templates",
        json={
            "key": "welcome",
            "version": 1,
            "content": "Hello, {{name}}",
            "locale": "ko",
            "is_active": True,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["key"] == "welcome"
    assert data["version"] == 1
    assert "id" in data

    # Retrieve template
    r2 = client.get("/admin/templates/welcome/1")
    assert r2.status_code == 200
    t = r2.json()
    assert t["key"] == "welcome"
    assert t["version"] == 1


def test_presentation_create_and_decide():
    # create two users
    u1 = client.post("/users/", json=_user_payload("alice", "alice_kakao", "01012341234"))
    assert u1.status_code == 200, u1.text
    id1 = u1.json()["id"]

    u2 = client.post("/users/", json=_user_payload("bob", "bob_kakao", "01056785678"))
    assert u2.status_code == 200, u2.text
    id2 = u2.json()["id"]

    # create presentation (proposal)
    p = client.post("/admin/presentations", json={"requester_id": id1, "candidate_id": id2})
    assert p.status_code == 200, p.text
    pdata = p.json()
    assert pdata["outcome"] == "pending"
    pid = pdata["id"]

    # list presentations for requester
    l = client.get(f"/admin/presentations?user_id={id1}&role=requester")
    assert l.status_code == 200
    items = l.json()
    assert any(item["id"] == pid for item in items)

    # decide presentation (accept)
    d = client.post(f"/admin/presentations/{pid}/decision", json={"outcome": "accepted"})
    assert d.status_code == 200, d.text
    decided = d.json()
    assert decided["outcome"] == "accepted"
    assert decided["decided_at"] is not None

    # cleanup small delay to ensure DB flush if necessary
    time.sleep(0.01)
