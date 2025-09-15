# 삭제 후보 전수조사 (초안)

작성일: 2025-09-16  
작성자: 자동 감사(1차, 정밀검토 필요)

이 문서는 코드베이스에서 "안전한 삭제 후보"를 분류하기 위한 1차 전수조사 결과입니다. 각 항목에 대해
- 파일 경로
- 심볼명(클래스/함수/엔드포인트 등)
- 참조 여부(레포 전체 검색 기준, 필요시 더 정밀한 정적/동적 분석 권장)
- 삭제 영향도(낮음/중간/높음) 및 간단한 근거

주의: 이 문서는 자동/수동 검색을 기반으로 한 1차 목록입니다. 삭제 전에는
- CI(테스트) 전체 실행
- 런타임 로그/운영 트래픽에서의 사용 여부 확인
- DB 마이그레이션/데이터 보존 영향 검토
를 반드시 수행하십시오.

메서드: repo-wide 텍스트 검색(정규표현식) 및 파일 목록/탐색을 통해 수집. 여러 곳에서 참조되는 항목은 "참조 있음"으로 표시. 참조가 발견되지 않은 항목은 "참조 없음(검색 기준)"으로 표시.

---

## 요약 체크리스트
- [x] 요구사항 분석
- [x] 레포 전체 검색(템플릿 / plan / present / presentation 관련)
- [x] 라우터의 직접 DB 접근 여부 검색(`db.query(`)
- [x] 1차 후보 목록 작성 (본 파일)
- [ ] 각 후보에 대해 더 정밀한 참조 검증 (eg. IDE refactor, grep -R, mypy/flake)
- [ ] CI/테스트 실행으로 삭제 영향 확인
- [ ] 런타임(로컬/스테이징)에서 기능 테스트 후 최종 삭제

---

## 1) 템플릿 관련 (CRUD 외의 API / 함수 / 클래스 / 엔드포인트)

- app/services/template_engine.py
  - 심볼: TemplateEngine (추정)
  - 참조 여부: 참조 있음 (app/services/messages.py, tests 등에서 사용 가능성)
  - 삭제 영향도: 중간 → 템플릿 렌더링 로직에 영향. template CRUD 를 삭제하더라도 렌더링 계층이 남아있다면 재사용됨. 사용 위치 확인 필요.

- app/services/messages.py
  - 심볼: 템플릿 로드/렌더링 래퍼 함수들 (load/render helper)
  - 참조 여부: 참조 있음 (matching, present 관련 서비스/라우터에서 사용)
  - 삭제 영향도: 높음 → 메시지/프레젠테이션 렌더링 전반에 영향. 삭제 불가(혹은 대체 구현 필요).

- app/db/tables/template.py
  - 심볼: Template DB 테이블 정의 (테이블명: `template` / `templates` 혼용 여부 주의)
  - 참조 여부: 참조 있음 (crud.get_template 등에서 사용)
  - 삭제 영향도: 높음 → DB 스키마 및 관련 CRUD 전반 영향. 스키마 자체를 제거하려면 DB 마이그레이션 필요.

- app/db/manager/template_manager.py
  - 심볼: TemplateManager (CRUD 트랜잭션 래퍼)
  - 참조 여부: 참조 있음 (routers/templates.py 등)
  - 삭제 영향도: 높음 → 템플릿 관련 관리자 제거 시 대체가 필요.

- app/routers/templates.py 및 app/routers/template_router.py
  - 심볼: `/template` 엔드포인트들 (create/get/patch/delete)
  - 참조 여부: 참조 있음 (main.py에서 include_router)
  - 삭제 영향도: 높음 → API 엔드포인트 제거 시 클라이언트 영향.

- app/crud.py 내 템플릿 관련 함수들
  - 심볼: create_template, get_template, list_templates, update_template 등
  - 참조 여부: 참조 있음
  - 삭제 영향도: 높음

노트: 템플릿에 관해서 'CRUD 외' 라고 명시되어 있어 템플릿 CRUD(관리 기능)는 보존 대상일 수 있음. 위 항목들은 템플릿 관련 비-CRUD 로직(렌더링/래퍼/매니저 등)을 모두 표기했으며, 실제 삭제 후보는 "참조 없음"인 항목에 한정해야 합니다.

---

## 2) plan / present / presentation 관련 모든 파일 / 라우트 / 서비스 (목록 및 상태)

(레포 내에서 `plan`, `present`, `presentation` 관련 파일들을 전수 기재)

- app/routers/plans.py
  - 심볼: /plans 엔드포인트 (create_plan, list_plans, get_plan)
  - 참조 여부: 참조 있음 (main.py include)
  - 삭제 영향도: 높음 (플랜 관련 API 제거)

- app/routers/present.py
  - 심볼: 엔드포인트들 (present_single, present_plan 등)
  - 참조 여부: 참조 있음
  - 삭제 영향도: 높음 (프레젠테이션 실행/커밋 관련 로직)

- app/routers/presentations.py
  - 심볼: /presentations 엔드포인트 (create_presentation, decide_presentation, list_pending_messages ...)
  - 참조 여부: 참조 있음
  - 삭제 영향도: 높음

- app/models.MatchPlan, app/models.Presentation
  - 심볼: ORM 모델 정의 (tables: plans, presentations)
  - 참조 여부: 참조 있음 (crud, routers)
  - 삭제 영향도: 높음 → DB 모델 제거는 마이그레이션·데이터 영향 큼

- app/schemas.MatchPlan, app/schemas.Presentation 등
  - 심볼: Pydantic 스키마들
  - 참조 여부: 참조 있음 (라우터/CRUD 응답/요청에 사용)
  - 삭제 영향도: 높음

- app/services/match_history.py
  - 심볼: presentation / match history 관련 CRUD 래퍼
  - 참조 여부: 참조 있음 (matching 로직과 분리된 부분)
  - 삭제 영향도: 중~높음 (매칭·프레젠테이션 흐름 영향)

- app/services/match_service.py, app/services/matching.py
  - 심볼: 매칭 로직, 프레젠테이션 생성/메시지 관련 처리
  - 참조 여부: 참조 있음
  - 삭제 영향도: 높음

- tests/test_templates_presentations.py
  - 심볼: 템플릿/프레젠테이션 관련 테스트
  - 참조 여부: 참조 있음
  - 삭제 영향도: 테스트 제거 영향(테스트 신뢰도 하락)

요약: plan/present/presentation 관련 대부분 파일은 활성 사용중. "삭제 후보"로 바로 옮기기에는 위험. 단, 내부의 일부 헬퍼/유틸(미사용 함수)는 후보가 될 수 있음 — 아래 3) 항목에서 확인.

---

## 3) 사용되지 않는 스키마 / 모델 / 유틸 함수 (가능성 있는 후보 — 추가 확인 필요)

아래 항목들은 레포 검색 기준으로 사용처가 적거나 보이지 않는(또는 파일 이름만 존재하고 호출 위치 적음) 경우입니다. "참조 없음"으로 표기된 항목은 수동/IDE 기반 전역 참조(정적) 확인과 런타임(테스트) 확인을 권장합니다.

- app/models/template_response.py
  - 심볼: (응답 모델들)
  - 참조 여부: 검색 기준 — 적음/없음(명확한 참조 없음)
  - 삭제 영향도: 낮음→중간 (문서/별도 API 응답에서만 사용될 수 있으므로 확인 필요)

- app/models/user_request.py / app/models/user_response.py
  - 심볼: DTO/모델 레이어
  - 참조 여부: 적음(대부분 app/schemas.py 와 중복 역할일 가능성)
  - 삭제 영향도: 낮음→중간 (사용 위치 확인 필요)

- app/models/history_request.py / app/models/history_response.py
  - 심볼: DTO들
  - 참조 여부: 적음(또는 history_router에서 Pydantic 스키마 대신 사용 여부 확인 필요)
  - 삭제 영향도: 낮음→중간

- app/models/match_response.py
  - 심볼: DTO
  - 참조 여부: 불명확(검색 필요)
  - 삭제 영향도: 낮음

- app/models/template_request.py
  - 심볼: DTO/요청 모델
  - 참조 여부: 불명확
  - 삭제 영향도: 낮음→중간

- app/services/template_engine.py 내부의 일부 유틸 함수(예: 오래된 포맷 도우미)
  - 심볼: 내부 헬퍼
  - 참조 여부: 일부만 참조됨
  - 삭제 영향도: 낮음 (만약 대체 로직이 있으면 삭제 가능)

권고 절차:
1. 각 후보 심볼에 대해 `git grep -n "<심볼명>"`으로 전역 참조 확인
2. IDE의 "Find Usages"로 정적 참조 탐지
3. 테스트 전체 실행(특정 테스트가 실패하면 해당 항목 복원)
4. 런타임 로그/운영에서 사용 여부 확인(특히 메시지/렌더링 관련)

---

## 4) 라우터에서 DB 직접 접근(잔존 코드)

목표: routers/*.py 에서 직접 `db.query(models.Xxx)` 처럼 DB를 직접 조작하는 코드가 남아있는지 확인.

결과(1차 자동 검색):
- `db.query(` 패턴을 app/routers/*.py에서 검색한 결과: 0건
- 대부분 라우터는 `Depends(get_db)`로 Session을 주입하지만 CRUD 또는 manager 레이어(crud.py / db/manager/*)를 통해 DB를 사용함
- 예외: 일부 라우터에서 `crud.get_plan(db, ...)` 같이 직접 CRUD 레이어를 호출하는 형태는 있음(그러나 이는 설계상 의도된 호출)

결론: 직접적인 `db.query(` 호출은 routers 디렉터리에서 발견되지 않았음(검색 기준). 따라서 "라우터에서 직접 DB 접근" 문제는 현재로서는 발견되지 않음.

권고: 라우터 내부에서 `db`를 받아 직접 모델 접근 또는 쿼리를 수행한 코드(직접 Session 쿼리)를 수동으로 한 번 더 살펴보십시오. 자동 검색은 문자열 패턴에 의존하므로 변수명/함수 포워딩으로 숨겨진 경우 놓칠 수 있음.

---

## 5) 기타 dead code (import만 되고 미사용 등)

아래는 파일 단위/모듈 단위로 "임포트만 되고 사용처가 거의 없는" 후보입니다. 추가 검증 권장.

- app/models/*.py (별도 DTO 파일들) — app/schemas.py와 역할 중복 가능 → 중복 제거 후보
  - 경로: app/models/template_response.py, app/models/user_request.py, app/models/user_response.py, app/models/history_request.py, app/models/history_response.py, app/models/match_response.py
  - 참조 여부: 검색 상 참조 빈도 낮음
  - 삭제 영향도: 낮음→중간 (문서/이전 API 호환성 고려)

- scripts/import_presentations.py
  - 심볼: 스크립트(데이터 임포트)
  - 참조 여부: 로컬 스크립트(운영 코드에서는 호출 안 될 가능성 높음)
  - 삭제 영향도: 낮음 (데이터 재현 필요시 보존 권장)

- scripts/import_excel.py, scripts/migrate_user_schema.py
  - 심볼: 유틸/마이그레이션 스크립트
  - 참조 여부: 로컬 전용, 운영 API와 독립
  - 삭제 영향도: 낮음 (하지만 보존 권장)

- app/services/user_management.py (내부 함수 중 일부)
  - 심볼: 특정 유틸 함수가 다른 모듈에서 참조되지 않음
  - 참조 여부: 검증 필요
  - 삭제 영향도: 낮음→중간

---

## 권장 작업 흐름 (안전하게 삭제하기 위한 단계)

1. 후보 선별: 이 문서에서 "참조 없음"으로 분류된 항목을 1차 목록으로 확정.
2. 정적 확인: IDE/grep으로 전역 참조 재검증.
3. 테스트: 전체 테스트(특히 integration/test_templates_presentations.py) 실행. 실패하는 테스트가 있으면 원복 혹은 더 조사.
4. 런타임(스테이징) 검증: 스테이징에 배포해 일정 기간 모니터링 (특히 템플릿/프레젠테이션 관련 이벤트).
5. 점진 삭제: 하나씩(또는 관련 그룹 단위) PR 생성 → CI 통과 → 스테이징에서 검증 → master에 병합.
6. DB 변경이 필요할 경우 데이터 백업/마이그레이션 스크립트 준비.

---

## 추가 메모 / TODOs (권장)
- [ ] 각 "참조 없음" 항목에 대해 `git grep -n "{심볼명}"` 결과 캡처 및 첨부
- [ ] tests/ 와 docs/ 내부의 레퍼런스도 확인 (문서에서만 사용되는 DTO 등)
- [ ] DB 스키마(테이블) 제거 전 데이터/마이그레이션 계획 수립
- [ ] 최종 삭제 PR에는 "soft-delete" 또는 deprecation 주석을 포함하여 운영 중단 위험 완화

---

끝.
