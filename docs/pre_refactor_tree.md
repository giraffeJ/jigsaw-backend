# 리포지토리 - 리팩터링 전 트리 (pre-refactor)

생성일: 2025-09-15 23:21:07 KST  
Git 커밋: c3d7c880d255dba32a10c0d617a81f3e6ca5eb6a

아래는 최상위 폴더와 주요 파일들의 목록입니다. (리팩터링 전에 구조를 백업/기록하기 위한 스냅샷)

## 최상위 항목
- .gitignore
- .pre-commit-config.yaml
- .python-version
- .env
- app.db
- app.db.bak
- main.py
- pyproject.toml
- README.md
- README_DOC.md
- uv.lock
- pytest_output.txt
- pytest_output2.txt
- pytest_output3.txt

## 디렉토리: app/
- app/__init__.py
- app/crud.py
- app/db.py
- app/main.py
- app/models.py
- app/schemas.py
- app/routers/
  - app/routers/__init__.py
  - app/routers/match.py
  - app/routers/plans.py
  - app/routers/present.py
  - app/routers/presentations.py
  - app/routers/templates.py
- app/services/
  - app/services/match_history.py
  - app/services/matching.py
  - app/services/messages.py
  - app/services/template_engine.py
  - app/services/user_management.py

## 디렉토리: docs/
- docs/CHANGELOG_PHASE1.md
- docs/import_excel_usage.md
- docs/matching_process.md

## 디렉토리: scripts/
- scripts/data.csv
- scripts/data.xlsx
- scripts/import_excel.py
- scripts/import_presentations.py

## 디렉토리: tests/
- tests/test_matching_core.py
- tests/test_same_workplace.py
- tests/test_templates_presentations.py
- tests/fixtures/
  - tests/fixtures/matching_data.py

---

참고:
- 위 목록은 최상위 폴더와 주요 소스/문서/스크립트/테스트 파일을 우선적으로 정리한 것입니다.
- 원하시면 더 세밀한 서브디렉토리 트리(모든 하위 파일 포함)를 추가로 기록해 드리겠습니다.
