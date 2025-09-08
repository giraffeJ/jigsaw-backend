# CHANGELOG — PHASE 1: Presentations / Templates / Plans 추가

날짜: 2025-09-08

요약:
- 제안/노출 이력(presentations), 템플릿 관리(templates), 배치 매칭 플랜(plans) 관련 DB 모델·스키마·CRUD·관리용 라우터(스텁) 추가.
- 최소한의 라우터(관리자용)로 템플릿 CRUD, 빈 플랜 생성/조회, 제안 생성/결정/조회 기능 제공.
- 테스트(간단한 happy-path) 추가 및 OpenAPI에 라우터 노출.

변경 상세
1. DB 모델 (app/models.py)
   - Template
     - 테이블명: `templates`
     - 필드: id (PK), key, version, locale, content, is_active, created_at, updated_at
     - UniqueConstraint: (key, version)
   - MatchPlan
     - 테이블명: `plans`
     - 필드: id (PK), created_by, notes, created_at
   - Presentation
     - 테이블명: `presentations`
     - 필드: id (PK), requester_id (FK users.id), candidate_id (FK users.id), plan_id (FK plans.id), template_key, template_version, rendered_message, outcome(enum pending/accepted/declined), presented_at, decided_at
     - UniqueConstraint: (requester_id, candidate_id, plan_id) — 동일 플랜 내 중복 노출 방지(스키마 레벨)
   - PresentationOutcome enum 추가

2. Pydantic 스키마 (app/schemas.py)
   - TemplateBase, TemplateCreate, TemplateUpdate, Template
   - MatchPlanBase, MatchPlanCreate, MatchPlan
   - PresentationBase, PresentationCreate, PresentationDecision, Presentation
   - Config: from_attributes=True로 DB model <-> response 모델 자동 변환 지원

3. CRUD 유틸 (app/crud.py)
   - Templates: create_template, update_template, get_template, list_templates
   - Plans: create_plan, get_plan, list_plans
   - Presentations: create_presentation, decide_presentation, list_presentations_for_user, get_presented_counts
   - 기존 사용자 CRUD/검색 유지

4. 라우터 스텁 (app/routers/)
   - templates.py
     - POST /admin/templates
     - GET  /admin/templates
     - GET  /admin/templates/{key}/{version}
     - PATCH /admin/templates/{key}/{version}
   - plans.py
     - POST /admin/match/plans
     - GET  /admin/match/plans
     - GET  /admin/match/plans/{plan_id}
   - presentations.py
     - POST /admin/presentations
     - POST /admin/presentations/{id}/decision
     - GET  /admin/presentations?user_id=&role=requester|candidate
   - app/main.py에서 라우터 포함(app.include_router)

5. 테스트 (tests/test_templates_presentations.py)
   - Template 생성/조회 happy path
   - Presentation 생성(pending) → 조회 → 결정(accepted) 시나리오
   - 테스트용 DB: sqlite 파일(`test_app.db`) 사용

주의사항 / 향후 작업
- DB 마이그레이션은 적용하지 않았습니다. 현재는 `models.Base.metadata.create_all()`로 테이블 생성합니다.
- Presentation 및 Plan의 실제 배치/매칭 로직은 Phase 2에서 구현 예정.
- get_presented_counts 집계는 Phase 2의 분포 로직에 사용될 예정.
- 관리자 인증/권한은 이 단계에서 구현하지 않았습니다(스텁 라우터는 관리용 경로로 네이밍됨).

권장 커밋 메시지 예시
- feat(models): add templates, plans, presentations tables
- feat(routers): add admin routers for templates, plans, presentations
- test: add basic tests for templates/presentations
- docs: add CHANGELOG_PHASE1
