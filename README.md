# Jigsaw Backend (매칭 시스템 백엔드)

FastAPI 기반 매칭 시스템 백엔드입니다. 이 문서에는 로컬 서버 실행 방법, 주요 엔드포인트, 엑셀/CSV 일괄 적재 스크립트 사용법, 그리고 스키마/마이그레이션 권장 사항을 정리해 두었습니다.

목차
- 개요
- 빠른 시작
- 의존성 설치
- 환경 변수 설정
- 개발 서버 실행
- 프로덕션 서버 실행
- 엑셀 / CSV -> DB 일괄 적재 (scripts/import_excel.py)
- DB 스키마 점검 / 권장 작업
- 주요 엔드포인트
- 개발 편의 커맨드
- 기타 참고사항

---

개요
- FastAPI, SQLAlchemy, Pydantic 기반의 REST API
- 기본 DB: SQLite (환경변수로 PostgreSQL/MySQL 설정 가능)
- 엑셀/CSV를 읽어 Pydantic 검증 후 DB에 일괄 삽입하는 스크립트를 제공

빠른 시작

1. 레포지토리 클론
```bash
git clone https://github.com/giraffeJ/jigsaw-backend.git
cd jigsaw-backend
```

2. 의존성 설치 (UV 사용 시)
```bash
uv sync
```
또는 pip 환경에서
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
(requirements.txt가 없으면 필요한 패키지를 개별 설치: fastapi, uvicorn, sqlalchemy, pydantic 등)

3. 추가 도구(엑셀 import용)
```bash
pip install pandas openpyxl xlrd
```

환경 변수
- 프로젝트 루트의 `.env` 파일을 사용합니다. 예:
```
DATABASE_URL=sqlite:///./app.db
DEBUG=True
SECRET_KEY=your-secret-key
HOST=0.0.0.0
PORT=8000
```
- PostgreSQL/MySQL 사용 시 `DATABASE_URL`을 적절히 교체하세요:
  - PostgreSQL: `postgresql://user:password@localhost/dbname`
  - MySQL: `mysql+pymysql://user:password@localhost/dbname`

개발 서버 실행
- uv(프로젝트에 포함된 스크립트 사용)
```bash
uv run dev
```
- 또는 직접 uvicorn 실행:
```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
# 또는
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- 접속:
  - API: http://localhost:8000
  - Swagger UI: http://localhost:8000/docs
  - Redoc: http://localhost:8000/redoc

프로덕션 서버 실행 (간단 예)
```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
# 또는 systemd / gunicorn + uvicorn workers 구성 권장
```

엑셀 / CSV -> DB 일괄 적재 (scripts/import_excel.py)
- 목적: 스프레드시트에 있는 사용자 데이터를 Pydantic으로 검증한 뒤 DB에 일괄 추가.
- 설치(필수): pandas, openpyxl, xlrd
```bash
pip install pandas openpyxl xlrd
```

- 스크립트 위치: `scripts/import_excel.py`
- 기본 사용법
  - dry-run (검증만 수행, DB에 쓰지 않음)
  ```bash
  python3 scripts/import_excel.py path/to/file.xlsx --dry-run
  ```
  - 실제 반영
  ```bash
  python3 scripts/import_excel.py path/to/file.xlsx
  ```
  - 옵션
    - `--sheet <시트명>`: 엑셀 파일에서 특정 시트 선택
    - `--chunk-size <숫자>`: 배치 커밋 단위 (기본 1000)

- 입력 스프레드시트 주의사항
  - 컬럼 헤더는 Pydantic 필드명과 일치해야 합니다. (예: nickname, kakao_id, phone_number, education_level, religion, smoking_status, workplace_matching, preferred_smoking 등)
  - 필수 필드(예시): nickname, privacy_consent, confidentiality_consent, real_name, kakao_id, phone_number, birth_year, height, residence, education_level, final_education, job_title, workplace, workplace_address, religion, smoking_status, preferred_age_range, workplace_matching, preferred_smoking
  - 전화번호 포맷은 schemas에서 정규식이 지정되어 있으므로(예: 010-xxxx-xxxx) 스크립트 실행 전 정규화 권장
  - Enum 필드(예: "흡연", "무교")는 문자열 값으로 적절히 기입되어야 합니다. 스크립트는 기본적인 enum 값 정규화를 시도합니다.

- 중복 처리
  - 동일한 kakao_id 또는 phone_number가 DB에 존재하면 해당 행은 건너뜁니다.
  - 파일 내 동일 키의 중복도 방지 처리를 합니다.

DB 스키마 점검 / 권장 작업
- 현재 상태
  - models.py와 schemas.py에 정의가 있으나, DB 제약(UNIQUE, CHECK 등)은 일부 부족합니다.
  - 현재 코드(개발 단계)에서는 `models.Base.metadata.create_all(bind=engine)`로 테이블 생성합니다.
  - 운영에서는 Alembic 같은 마이그레이션 도구 사용을 권장합니다.

- 우선 권장 변경 사항
  1. `kakao_id`, `phone_number`에 DB-level UNIQUE 제약 추가 (중복 방지)
  2. 전화번호 정규화/검증 로직을 DB 또는 import 스크립트에서 강화
  3. `preferred_age_range` 문자열 대신 `preferred_age_min`, `preferred_age_max` 정수 컬럼 사용 검토 (쿼리 효율 개선)
  4. 검색에 자주 쓰이는 컬럼들에 인덱스 추가 (residence, education_level, religion 등)
  5. 운영 DB에 대해 Alembic으로 마이그레이션 관리 (schema 변경시 안전성 확보)

주요 엔드포인트 (요약)
- GET /                   — 환영 메시지
- GET /health             — 헬스체크
- POST /users/            — 사용자 등록 (schemas.UserCreate)
- GET /users/             — 공개 사용자 목록 (schemas.UserPublic)
- GET /users/{user_id}    — 사용자 상세 (schemas.User)
- PUT /users/{user_id}    — 사용자 수정
- DELETE /users/{user_id} — 사용자 비활성화
- GET /users/{user_id}/matches — 매칭 후보 조회
- GET /search/users       — 조건별 사용자 검색

개발 편의 커맨드
- 서버 실행 (dev)
  - `uv run dev`
  - `python -m uvicorn app.main:app --reload`
- import 스크립트 (dry-run)
  - `python3 scripts/import_excel.py data/users.xlsx --dry-run`
- import 스크립트 (실제 반영)
  - `python3 scripts/import_excel.py data/users.xlsx`
- 의존성 설치 (pandas 등)
  - `pip install pandas openpyxl xlrd`
- DB 스키마 자동 생성 (개발용)
  - 앱 실행 시 `models.Base.metadata.create_all(bind=engine)`가 호출되어 로컬 DB를 만듭니다.

기타 참고사항 / 권고
- 운영 DB에서는 `create_all` 대신 Alembic 사용을 권장합니다. 특히 UNIQUE 제약 추가 전에는 기존 데이터 정리(중복 제거)를 반드시 수행해야 합니다.
- 대량(수만 건 이상) 적재는 CSV로 변환 후 DB 네이티브 bulk 로드(Postgres COPY 등)를 사용하는 것이 훨씬 빠릅니다.
- 스크립트를 실행하기 전에 `.env`에 DB 연결 문자열을 맞춰 두거나 환경변수를 설정하세요.
- 문제 발생 시: 먼저 dry-run을 돌려서 validation 에러를 확인하고, 샘플 몇 건으로 실제 반영해본 뒤 전체 적재를 수행하세요.

문의 / 다음 작업 제안
- import 스크립트 실제 데이터(demo)로 테스트 및 에러 수정
- Alembic 마이그레이션 파일 생성 (UNIQUE 제약 등)
- preferred_age_range 정규화(모델/스키마/마이그레이션)

---
프로젝트에 README를 업데이트했습니다. 추가로 README에 넣을 예시 CSV/엑셀 템플릿(헤더 포함)을 원하시면 생성해 드리겠습니다.
