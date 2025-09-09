매칭 프로세스 — 클래스/함수 단위 설명서
===================================

개요
----
이 문서는 현재 코드베이스(app/services/matching.py)에 구현된 매칭 핵심 로직을 클래스/함수 단위로 설명하고, 입력/출력, 내부 알고리즘(특히 '같은 직장' 판정 로직)과 테스트 방법을 정리합니다. 목표는 유지보수자가 매칭 로직을 빠르게 이해하고 TC(테스트 케이스)를 작성/확장할 수 있게 하는 것입니다.

핵심 함수 및 역할
-----------------

1) mutual_candidates(db: Session, requester: models.User, cooldown_days: int, limit: int) -> List[Dict[str, Any]]
- 역할: 요청자(requester)에 대해 상호(상호호환) 조건을 만족하는 후보자 목록을 생성.
- 입력:
  - db: SQLAlchemy 세션
  - requester: 매칭을 요청하는 User 모델 인스턴스
  - cooldown_days: 최근 N일간 이미 제시된 후보는 제외하기 위한 쿨다운(정수)
  - limit: 반환할 최대 후보 수
- 출력: 후보 목록(각 항목은 dict)
  - candidate_id: 후보 사용자 id
  - score: 정렬에 사용되는 실수 점수
  - reasons: 후보가 선정된/제외된 근거 목록(예: "지역 근접")
  - presented_count: 이 후보가 지금까지 얼마나 많이 제시되었는지
  - last_presented_at: 마지막 제시 시각 (없을 수 있음)
- 흐름 요약:
  1. crud.get_users_for_matching(...)로 후보 풀 수집 (자기 자신 제외 등)
  2. 쿨다운 적용: 최근에 requester에게 제시된 candidate_id 집합을 crud.list_recent_presented_candidate_ids로 조회하여 제외
  3. 후보별로 _satisfy_preference(requester, candidate) 및 _satisfy_preference(candidate, requester)를 호출하여 상호 선호 검증 (A->B, B->A 둘다 만족해야 후보로 인정)
  4. 후보별 점수(score) 계산 (현재는 "지역 근접"이면 +0.1)
  5. 후보를 정렬: presented_count(오름차순), last_presented_at(오래된 순), score(내림차순)
  6. 상위 limit개를 반환

2) _satisfy_preference(a: models.User, b: models.User) -> Tuple[bool, List[str]]
- 역할: 사용자 a 입장에서 사용자 b가 a의 선호 조건을 만족하는지 여부를 검사
- 반환: (ok: bool, reasons: List[str]) — ok가 True면 b는 a의 조건을 만족
- 검사 항목:
  - 출생연도 범위(preferred_age_min / preferred_age_max): 값이 지정되면 b.birth_year가 범위 내여야 함. (min>max인 경우 스왑)
  - 거주지 근접: a.residence와 b.residence가 부분문자열로 포함되면 "지역 근접"을 reasons에 추가 (이 경우 매칭 허용 여부에 영향은 없음, 단지 이유로 표시)
  - 흡연 선호(preferred_smoking): a.preferred_smoking은 CSV 또는 리스트로 저장 가능. b.smoking_status의 value가 허용 목록 중 하나여야 함.
  - 종교 선호(preferred_religion): preferred_religion은 CSV. b.religion의 value가 허용 목록 중 하나여야 함.
  - 같은 직장 허용 여부(workplace_matching):
    - a.workplace_matching 값이 "같은 직장 불가능"일 경우 a.workplace와 b.workplace를 비교하여 같은 회사면 ok=False로 처리.
    - 같은 회사 판정 알고리즘:
      1. _normalize_workplace(s: str)로 소문자화, 회사 식별자(예: "㈜", "(주)", "주식회사", "주식" 등)와 문장부호 제거, 알파벳/숫자/공백만 남김, 연속 공백 정리.
      2. 정규화 문자열 na, nb가 동일하거나 부분 문자열 포함(na in nb or nb in na)이면 같은 회사로 판단.
      3. 아니면 단어 토큰(공백 분리)의 교집합이 있으면 같은 회사로 판단(token intersection heuristic).
    - 같은 회사로 판단되면 a가 "같은 직장 불가능"을 선언했으므로 ok=False.

3) _in_range(v: Optional[int], lo: Optional[int], hi: Optional[int]) -> bool
- 역할: 정수 v가 [lo, hi] 범위(각각 None 가능)에 속하는지 검사. v가 None이면 False 반환.

데이터/의존성
-------------
- models.User: app/models.py에서 정의된 SQLAlchemy 모델. 핵심 필드:
  - id, birth_year (int), residence (str), workplace (str), workplace_matching (WorkplaceMatching enum)
  - smoking_status (SmokingStatus enum), religion (Religion enum)
  - preferred_age_min, preferred_age_max (int 또는 None)
  - preferred_smoking (CSV string), preferred_religion (CSV string)
- crud 모듈: matching.py는 crud 모듈의 다음 함수/데이터를 사용:
  - get_users_for_matching(db, exclude_user_id, skip, limit)
  - list_recent_presented_candidate_ids(db, requester_id, since_dt)
  - get_presented_counts_by_candidate(db)
  - get_last_presented_at_by_candidate(db)

정렬 및 점수화 전략(현재 구현)
-----------------------------
- score 시작값 0.0
- "지역 근접" 이유가 발견되면 +0.1
- 정렬 우선순위:
  1. presented_count 오름차순 (적게 노출된 후보를 우선)
  2. last_presented_at 오래된 순 (오래된 후보를 우선)
  3. score 내림차순

같은 직장 판정 세부 예시
-----------------------
정규화 예:
- "주식회사 ABC 주식회사" -> "abc"
- "(주) ABC" -> "abc"
- "ABC Technologies Co." -> "abc technologies co"
- "Technologies ABC Co." -> "technologies abc co"

판정:
- na == nb 또는 na in nb 또는 nb in na -> 같은 회사
- or (set(na.split()) & set(nb.split())) != ∅ -> 같은 회사 (토큰 교집합 히어리스틱)

테스트(같은 직장 판단) 작성 가이드
-------------------------------
- 테스트 파일 예: tests/test_same_workplace.py (저장됨)
- 주요 시나리오:
  1. requester가 "같은 직장 불가능"인 경우, 동일 회사(정규화/토큰변형 포함) 후보는 결과에서 제외되어야 함.
  2. requester가 "같은 직장 가능"인 경우 동일 회사 후보는 포함되어야 함.
  3. 토큰 교집합(예: "ABC Technologies" vs "Technologies ABC Co.")로도 같은 회사로 판단되어야 함.
- 테스트 방법:
  1. TestClient를 사용해 /users/ 엔드포인트로 사용자 생성
  2. requester에 대해 /users/{id}/candidates?limit=X&cooldown_days=Y 호출하여 후보 목록을 조회
  3. candidate_id 목록에서 동일 회사 후보의 포함/제외를 assert

확장 포인트 및 권장 리팩토링
--------------------------
- 현재 matching.py는 유저/매칭이력/안내문(템플릿)을 직접 참조하는 여러 CRUD 지점을 사용. 유지보수성을 높이려면 다음과 같이 책임을 분리 권장:
  1. app/services/user_management.py: User 생성/검색/정규화 관련 로직 (ex. workplace normalization 함수 이동)
  2. app/services/match_history.py: presented_count, last_presented_at, 최근 제시 내역 조회 등 프레젠테이션 이력 관련 CRUD 래핑
  3. app/services/messages.py: 템플릿 로딩/렌더링, 안내문 관리
  4. app/services/matching.py: 오직 매칭 알고리즘(조건검증, 점수화, 정렬)만 담당
- 장점: 각 모듈 단위 테스트 추가 용이, 중복 코드 축소, 명확한 책임 분리

운영/테스트 실행 방법
--------------------
- 로컬 테스트 DB를 사용하려면 환경변수 DATABASE_URL을 sqlite 파일로 지정:
  - 예: DATABASE_URL=sqlite:///./test_app.db pytest -q
- 단일 테스트 파일만 실행:
  - pytest tests/test_same_workplace.py -q
- 전체 테스트:
  - pytest -q

부록: 매칭 관련 엔드포인트 (참고)
-------------------------------
- GET /users/{id}/candidates?limit={limit}&cooldown_days={days}
  - mutual_candidates를 래핑한 엔드포인트(라우터에서 crud 호출/세션관리 포함)
- 관리자용 프레젠테이션 생성: POST /admin/presentations (테스트에서 사용됨)

결론
----
현재 매칭 흐름은 비교적 직관적이며 같은 직장 판정은 비교적 보수적인(동일/부분문자열/토큰 교집합) 방식으로 동작합니다. 향후 정교화(예: 회사명 매칭을 위한 외부 정규화 DB, 토큰 표준화/불용어 제거 등)를 고려할 수 있습니다.
