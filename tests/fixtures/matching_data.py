"""
테스트용 매칭 데이터 및 헬퍼 함수

의도:
- TestClient를 사용하는 테스트에서 중복되는 payload 생성과 사용자/프레젠테이션 생성을 단순화.
- 동일 직장 판정, 쿨다운, presented_count 등 매칭 시나리오를 만들기 위한 유틸 제공.

사용법 예:
from fastapi.testclient import TestClient
from tests.fixtures.matching_data import make_user_payload, create_users, create_presentation

client = TestClient(main.app)
payloads = [make_user_payload(...) ...]
created = create_users(client, payloads)
create_presentation(client, requester_id, candidate_id)

작성된 함수:
- make_user_payload(...)
- create_users(client, payload_list) -> list of created user dicts
- create_presentation(client, requester_id, candidate_id, plan_id=None) -> response.json()

주의:
- 이 모듈은 테스트 환경(TestClient)을 가정합니다.
- 응답 검증(HTTP 200)은 내부에서 수행하므로 테스트에서 별도 assert를 줄일 수 있습니다.
"""

from typing import Any, Dict, List, Optional


def make_user_payload(
    nickname: str,
    kakao_id: str,
    phone: str,
    birth_year: int = 1990,
    residence: str = "서울",
    smoking: str = "비흡연",
    religion: str = "무교",
    workplace: str = "회사",
    workplace_matching: str = "같은 직장 가능",
    education_level: str = "대학교",
) -> Dict[str, Any]:
    """
    공통 user 생성 payload 반환
    """
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
        "education_level": education_level,
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


def create_users(client, payloads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    TestClient를 사용해 /users/ 엔드포인트로 다수의 사용자를 생성.
    - payloads: make_user_payload로 만든 리스트
    - 반환: 생성된 user 객체(dict) 리스트
    내부에서 응답 상태코드(200)를 assert 함.
    """
    created = []
    for p in payloads:
        resp = client.post("/users/", json=p)
        assert resp.status_code == 200, f"Failed to create user: {resp.status_code} {resp.text}"
        created.append(resp.json())
    return created


def create_presentation(
    client, requester_id: int, candidate_id: int, plan_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    /admin/presentations 엔드포인트를 사용하여 프레젠테이션을 생성.
    - 반환: 응답 json
    내부에서 응답 상태코드(200)를 assert 함.
    """
    payload = {"requester_id": requester_id, "candidate_id": candidate_id}
    if plan_id is not None:
        payload["plan_id"] = plan_id
    resp = client.post("/admin/presentations", json=payload)
    assert resp.status_code == 200, f"Failed to create presentation: {resp.status_code} {resp.text}"
    return resp.json()
