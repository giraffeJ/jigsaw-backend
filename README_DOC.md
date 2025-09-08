# Jigsaw-backend — 코드 구조 및 상세 설명

이 문서는 프로젝트의 소스 구조와 각 파일의 목적, 파일에 포함된 클래스 및 함수(시그니처)와 그 동작/구성에 대해 가능한 자세하게 정리한 문서입니다. 주로 `app/` 디렉토리와 `scripts/import_excel.py`를 중심으로 설명합니다.

목차
- 개요
- 프로젝트 루트 파일
- app 패키지
  - app/__init__.py
  - app/db.py
  - app/models.py
  - app/schemas.py
  - app/crud.py
  - app/main.py
- scripts
  - scripts/import_excel.py
- 운영/주의사항 요약

---

개요
- 이 프로젝트는 FastAPI 기반의 "매칭(소개팅) 시스템" 백엔드입니다.
- SQLAlchemy ORM으로 DB 모델을 정의하고, Pydantic 스키마로 입력/출력을 검증합니다.
- 기본 DB는 SQLite를 사용하도록 설정되어 있으나 환경 변수 `DATABASE_URL`로 다른 DB를 지정할 수 있습니다.
- 대량 입력 지원을 위한 Excel/CSV -> DB import 스크립트가 포함되어 있습니다.

프로젝트 루트 파일 (간단)
- README.md : (원본) 프로젝트 요약.  
- README_DOC.md : (이 문서) 코드 구조 상세 설명 출력 파일.  
- pyproject.toml, .python-version 등: 파이썬/패키지 설정 파일.  
- app.db : (로컬 SQLite DB 파일; 개발 환경에서 생성됨)
- main.py : (루트) — 보통 FastAPI 앱 진입점이 `app/main.py`에 있으므로 루트 `main.py`는 보조/다른 용도일 수 있음.

---

app 패키지

1) app/__init__.py
- 현재 특별한 내용 없음(빈 파일 또는 모듈 초기화만 수행).
- 역할: `app` 패키지를 파이썬 패키지로 인식하게 함. (추후 패키지 초기화 코드 추가 가능)

2) app/db.py
- 역할: 데이터베이스 연결/세션/베이스 클래스 정의.
- 주요 내용:
  - SQLALCHEMY_DATABASE_URL: 환경 변수 `DATABASE_URL`을 읽어 DB URL 결정. 기본값: `sqlite:///./app.db`
  - engine: SQLAlchemy `create_engine` 객체.
    - SQLite일 경우 `connect_args={"check_same_thread": False}` 설정.
  - SessionLocal: `sessionmaker(autocommit=False, autoflush=False, bind=engine)` — DB 세션 팩토리.
  - Base: `declarative_base()` — ORM 모델의 베이스 클래스.
- 주의:
  - 배포 시에는 SQLite 대신 PostgreSQL/MySQL 등을 사용하도록 `DATABASE_URL`을 설정해야 함.
  - 여러 스레드/프로세스 환경에서는 DB 연결 설정을 재검토 해야 함.

3) app/models.py
- 역할: SQLAlchemy ORM 모델 및 Enum 정의.
- 주요 구성요소:
  - Enum 클래스 (Python enum.Enum 사용)
    - EducationLevel: HIGH_SCHOOL("고등학교"), COLLEGE("전문대"), UNIVERSITY("대학교"), GRADUATE("대학원")
    - SmokingStatus: SMOKER("흡연"), NON_SMOKER("비흡연"), OCCASIONAL("가끔")
    - Religion: NONE("무교"), CHRISTIAN("기독교"), CATHOLIC("천주교"), BUDDHIST("불교"), OTHER("기타")
    - WorkplaceMatching: POSSIBLE("같은 직장 가능"), IMPOSSIBLE("같은 직장 불가능")
  - User 모델 (테이블명: `users`)
    - id: Integer, PK, index
    - nickname: String(100), not null — 카카오톡 오픈채팅 닉네임 (공개)
    - referrer_info: Text, nullable — 추천인 정보
    - privacy_consent: Boolean, default False, not null — 개인정보 수집 동의
    - confidentiality_consent: Boolean, default False, not null — 정보 유출 책임 동의
    - real_name: String(100), not null — 실명 (비공개)
    - kakao_id: String(100), not null — 카카오톡 ID (본인확인용)
    - phone_number: String(20), not null — 전화번호 (본인확인용)
    - birth_year: Integer, not null — 출생연도 (공개)
    - height: Integer, not null — 키(cm)
    - residence: String(200), not null — 거주지 (구 단위)
    - education_level: Enum(EducationLevel), not null — 학력
    - final_education: String(200), not null — 최종 학력(학교명)
    - job_title: String(200), not null — 직업
    - workplace: Text, not null — 직장(상세)
    - workplace_address: String(200), not null — 근무지 주소
    - religion: Enum(Religion), not null
    - smoking_status: Enum(SmokingStatus), not null
    - mbti: String(4), nullable — MBTI (선택)
    - hobbies: Text, nullable — 취미
    - additional_info: Text, nullable — 기타 자유기술
    - preferred_age_min / preferred_age_max: Integer, nullable — 선호 출생연도 범위(정수)
    - workplace_matching: Enum(WorkplaceMatching), not null — 같은 직장 매칭 허용 여부
    - preferred_smoking: Enum(SmokingStatus), not null — 선호 흡연 여부
    - preferred_religion: String(200), nullable
    - additional_matching_condition: Text, nullable
    - is_active: Boolean, default True — 사용자 활성화 여부(삭제 대신 비활성화)
    - created_at: DateTime(timezone=True), server_default=func.now()
    - updated_at: DateTime(timezone=True), onupdate=func.now()
- 주석/코멘트:
  - 모델 필드에 한국어 comment가 달려 있어 DB에 주석으로 남게 됨(사용하는 DB가 comment를 지원할 경우).
- 설계 메모:
  - 개인정보(실명, 카카오ID, 전화번호)는 DB에 저장되지만 공개 API는 `UserPublic`/필터링된 정보만 반환하도록 설계됨.
  - 선호 연령대는 birth_year(사용자)와 같은 정수 형태(연도)를 사용하도록 설계됨.

4) app/schemas.py
- 역할: Pydantic 기반 입력/출력 검증 및 직렬화 스키마 정의.
- 주요 구성요소:
  - Enum(str, Enum) 형태의 Pydantic enum: EducationLevel, SmokingStatus, Religion, WorkplaceMatching (schemas 전용; 모델의 Enum과 유사하지만 Pydantic 친화적).
  - UserBase (BaseModel)
    - 사용자 생성/기본 속성 (create/공개 포함)
    - 필드 및 검증:
      - nickname: str (required)
      - referrer_info: Optional[str]
      - privacy_consent: bool (required)
      - confidentiality_consent: bool (required)
      - real_name: str (required)
      - kakao_id: str (required)
      - phone_number: str (required) — 정규식 패턴: ^(\d{9,11}|0\d{1,2}-\d{3,4}-\d{4})$
      - birth_year: int (ge=1950, le=2010)
      - height: int (ge=140, le=220)
      - residence: str
      - education_level: Union[EducationLevel, str] — Enum 또는 자유 입력 허용
      - final_education: str
      - job_title: str
      - workplace: str
      - workplace_address: str
      - religion: Union[Religion, str]
      - smoking_status: Union[SmokingStatus, str]
      - mbti, hobbies, additional_info: Optional[str]
      - preferred_age_min/ preferred_age_max: Optional[int]
      - workplace_matching: Union[WorkplaceMatching, str]
      - preferred_smoking: Union[SmokingStatus, str]
      - preferred_religion, additional_matching_condition: Optional[str]
  - UserCreate(UserBase): 사용자 생성용(변경 없음, 그대로 사용)
  - UserUpdate(BaseModel): 부분 업데이트를 위한 Optional 필드 집합 (본인확인용 정보는 수정 불가하도록 설계되어 있음)
    - 수정 가능한 필드: nickname, referrer_info, 공개 인적사항(키/거주지/학력 등), 매칭조건, is_active
  - User(UserBase): DB에서 반환되는 전체 사용자 스키마
    - id: int, is_active: bool, created_at: datetime, updated_at: Optional[datetime]
    - Config: from_attributes = True (ORM 객체에서 attribute 기반으로 읽도록 설정)
  - UserPublic(BaseModel): 공개해서 반환 가능한 필드만 포함(매칭에 사용)
    - id, nickname, birth_year, height, residence, education_level, final_education, job_title, religion, smoking_status, mbti, hobbies, additional_info
    - Config: from_attributes = True
- 설계 메모:
  - 스키마는 Enum/자유입력 조합을 허용하여 다양한 입력(예: "대학교", "대졸")을 처리할 수 있도록 유연하게 설계됨.
  - UserCreate에서 필수 필드를 강제하고 import 스크립트에서 이 스키마로 검증함.

5) app/crud.py
- 역할: DB에 대한 CRUD 로직(비즈니스 로직이 간단히 들어감).
- 주요 함수와 동작:
  - get_user(db: Session, user_id: int) -> Optional[models.User]
    - user_id로 사용자 조회, `.first()` 반환
  - get_user_by_kakao_id(db: Session, kakao_id: str) -> Optional[models.User]
    - kakao_id로 조회 (중복 체크 등에서 사용)
  - get_user_by_phone(db: Session, phone_number: str) -> Optional[models.User]
    - 전화번호로 조회
  - get_user_by_nickname(db: Session, nickname: str) -> Optional[models.User]
    - 닉네임으로 조회
  - get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]
    - 활성(is_active == True) 사용자 목록 페이징 조회
  - get_users_for_matching(db: Session, exclude_user_id: int, skip: int = 0, limit: int = 100) -> List[models.User]
    - 매칭 대상 사용자 조회(본인 제외, 활성 사용자, privacy_consent 및 confidentiality_consent가 True인 사용자만 해당)
    - 반환: List[User]
  - create_user(db: Session, user: schemas.UserCreate) -> models.User
    - 중복 체크: kakao_id 및 phone_number 중복 검사. 중복이면 ValueError 발생.
    - new User 인스턴스 생성: models.User(**user.dict()), 세션에 추가 후 commit, refresh, 반환.
    - 예외: 중복일 경우 ValueError 발생 -> FastAPI에서 400 처리.
  - update_user(db: Session, user_id: int, user: schemas.UserUpdate) -> Optional[models.User]
    - 해당 사용자 존재 확인. 존재 시 `user.dict(exclude_unset=True)` 로 업데이트할 필드만 적용( setattr ), commit, refresh 후 반환.
    - 존재하지 않으면 None 반환.
  - delete_user(db: Session, user_id: int) -> bool
    - 실제 삭제가 아닌 `is_active = False`로 비활성화 처리, commit, True 반환.
    - 사용자 미존재 시 False 반환.
  - search_users_by_criteria(db: Session, birth_year_min: Optional[int]=..., ...) -> List[models.User]
    - 매칭 조건(출생연도/키/거주지/학력/종교/흡연여부 등)에 따른 필터링 쿼리 구성.
    - 기본 filter: is_active == True, privacy_consent == True, confidentiality_consent == True
    - 전달된 파라미터에 따라 `>=` / `<=` / `.contains()` / == 필터 적용.
    - 결과는 offset/limit 적용 후 `.all()` 반환.
- 주의:
  - create_user에서 ValueError로 중복을 처리하므로 API 레이어에서 HTTPException으로 변환해야 함(실제 변환은 app/main.py에 구현됨).
  - update_user는 모든 필드를 자유롭게 setattr하기 때문에 입력 검증(스키마)은 API 레이어에서 이미 수행되어야 함.

6) app/main.py
- 역할: FastAPI 애플리케이션과 라우트 정의.
- 핵심 구성:
  - models.Base.metadata.create_all(bind=engine) : 앱 시작 시 테이블 생성(동기적)
  - FastAPI 인스턴스 생성(title/description/version)
  - get_db dependency: SessionLocal() 생성/종료(try/finally)를 통해 DB 세션 주입
- 주요 엔드포인트:
  - GET "/" -> read_root()
    - 간단한 환영 메시지 반환
  - GET "/health" -> health_check()
    - {"status":"healthy"} 반환
  - POST "/users/" -> create_user(user: schemas.UserCreate, db: Session = Depends(get_db))
    - 사용자 등록
    - crud.create_user 호출, ValueError 발생 시 HTTPException(400) 반환
    - response_model: schemas.User (생성된 전체 사용자 데이터 반환)
  - GET "/users/" -> read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db))
    - 활성 사용자 목록(공개 정보) 반환
    - response_model: List[schemas.UserPublic]
    - crud.get_users 사용
  - GET "/users/{user_id}" -> read_user(user_id: int)
    - 사용자 상세 조회(response_model: schemas.User)
    - 사용자가 없으면 404 반환
  - PUT "/users/{user_id}" -> update_user(user_id: int, user: schemas.UserUpdate)
    - 사용자 정보 수정, 존재하지 않으면 404
    - response_model: schemas.User
  - DELETE "/users/{user_id}" -> delete_user(user_id: int)
    - 사용자 비활성화(soft delete)
    - 404 if not found
  - GET "/users/{user_id}/matches" -> get_user_matches(user_id: int, skip: int = 0, limit: int = 20)
    - 특정 사용자의 매칭 후보 목록(본인 제외)
    - 내부적으로 crud.get_users_for_matching 호출
    - response_model: List[schemas.UserPublic]
  - GET "/search/users" -> search_users(...) (다수의 optional 쿼리 파라미터: birth_year_min/max, height_min/max, residence, education_level, religion, smoking_status, skip, limit)
    - 조건에 따라 사용자를 검색(crud.search_users_by_criteria)
    - response_model: List[schemas.UserPublic]
- 주의:
  - `models.Base.metadata.create_all(bind=engine)`는 개발 환경에서 편리하지만, 마이그레이션 도구(예: Alembic)를 사용하면 더 안전하고 관리 가능한 DB 스키마 변경 관리가 가능함.

---

scripts/import_excel.py
- 역할: Excel(.xls/.xlsx)/CSV 파일을 읽어 다수의 사용자 레코드를 DB에 일괄 삽입하는 도구.
- 사용법:
  - pip install pandas openpyxl xlrd
  - python scripts/import_excel.py path/to/file.xlsx --sheet Sheet1
  - python scripts/import_excel.py path/to/file.csv
  - 옵션: --dry-run (검증만 수행), --chunk-size (커밋 배치 크기, 기본 1000)
- 핵심 기능:
  - load_dataframe(path, sheet): 파일 확장자에 따라 pandas.read_excel 또는 pandas.read_csv로 DataFrame 로드.
  - normalize_phone(phone): 전화번호 정규화 로직(숫자만 추출, 길이에 따른 하이픈 포맷 적용, Excel이 앞 0을 제거한 경우 보정 등).
  - normalize_enum(enum_cls, value): 모델의 enum Enum 클래스에 대해 유연한 정규화(약어, 변형값, 부분 문자열 매칭, 한국어 약어 매핑 등)를 수행.
  - parse_bool(v): 다양한 표현(예/아니오, true/false, 1/0 등)을 boolean으로 변환 시도.
  - validate_and_prepare_row(row): 한 행(row dict)을 받아 필수/옵션 필드 처리, 타입 변환(숫자를 int로), phone normalization, enum 사전처리, Pydantic(UserCreate) 검증을 수행. 성공하면 `prepared` dict 반환, 실패하면 에러 문자열 반환.
    - Pydantic 검증 이후 추가로 모델 Enum(모듈의 enum)과 매칭시키는 작업 수행.
    - enum 변환 실패 시 에러 처리하여 row를 건너뜀.
  - bulk_import(path, sheet, dry_run, chunk_size):
    - DataFrame 비어있으면 종료
    - 필수 컬럼(nickname, kakao_id, phone_number) 존재 여부 확인
    - 파일 내 고유 kakao_id/phone을 취합하여 DB에 이미 존재하는 레코드는 스킵 (중복 방지)
    - 각 행에 대해 validate_and_prepare_row 실행 → models.User(**prepared) 로 모델 인스턴스 생성 후 to_insert 목록에 추가
    - chunk_size마다 세션에 add_all(commit) 수행. dry_run이면 커밋하지 않음.
    - 최종 통계(총 행수, 삽입/스킵/검증오류 등) 출력
- 주의/세부사항:
  - Excel에서 숫자/문자 타입이 섞여 들어올 수 있으므로 문자열/숫자 처리(예: 전화번호, birth_year, height)를 세심히 다룸.
  - enum 필드는 다수의 한국어 표현을 정규화하도록 매핑 테이블과 heuristics를 사용.
  - 중복 판정은 현재 DB 내 kakao_id 또는 phone_number 중복 기준으로 파일 내/DB 중복을 피함.
  - 유효성 검사 실패(필수 필드 누락, enum 변환 실패 등)는 validation_errors 리스트에 기록되며 삽입되지 않음.
  - 기본적으로 스크립트는 프로젝트 루트를 sys.path에 추가하여 `from app import ...`가 작동하도록 함.

---

운영 / 주의사항 요약
- 개인정보 보호
  - `real_name`, `kakao_id`, `phone_number`는 DB에 저장되지만 공개 API(`UserPublic`)에서는 제외됩니다. 운영 시 DB 접근 통제와 백업 보안이 필수입니다.
- 마이그레이션
  - 현재는 `models.Base.metadata.create_all()`로 테이블을 생성합니다. 스키마 변경 및 운영 배포시 Alembic 같은 마이그레이션 툴 도입 권장.
- 데이터 검증
  - Pydantic 스키마(`schemas.UserCreate`)로 입력을 검증합니다. import 스크립트는 사전 정규화 + Pydantic 검증 + 모델 Enum 정규화를 수행합니다.
- 트랜잭션/동시성
  - bulk import는 chunk 단위로 commit을 수행합니다. 실패시 rollback 처리(try/except에서 rollback 호출)합니다. 대량 삽입 시 DB 락/성능을 고려해야 합니다.
- Enum/자유 입력
  - 스키마는 Enum 또는 자유 입력(str)을 허용하는 필드를 포함합니다. 이는 사용자 입력의 유연성을 제공하지만, 내부적으로는 `models.*` Enum으로 정규화하려는 시도가 있습니다. 정규화에 실패하면 에러가 발생하거나 자유 문자열로 남게 될 수 있으니 운영 규칙을 정의하세요(예: 허용 문자열 집합).
- 국제화/인코딩
  - 주석과 필드값에 한국어가 포함되어 있으므로 외부 시스템과 연동할 때 인코딩/문자열 처리에 주의가 필요합니다.

---

참고: 주요 함수/엔드포인트 빠른 요약
- CRUD
  - create_user(db, user: UserCreate) -> models.User
  - get_user(db, user_id) -> models.User | None
  - get_users(db, skip, limit) -> List[User] (활성 사용자)
  - update_user(db, user_id, user: UserUpdate) -> models.User | None
  - delete_user(db, user_id) -> bool (soft delete: is_active=False)
  - search_users_by_criteria(db, birth_year_min?, height_max?, residence?, ...) -> List[User]
- API
  - POST /users/ (body: UserCreate) -> User
  - GET /users/ -> List[UserPublic]
  - GET /users/{user_id} -> User
  - PUT /users/{user_id} (body: UserUpdate) -> User
  - DELETE /users/{user_id} -> message
  - GET /users/{user_id}/matches -> List[UserPublic]
  - GET /search/users?birth_year_min=...&height_max=... -> List[UserPublic]

---

문서 작성자 메모
- 이 문서는 소스 코드(2025-09-08) 기준으로 자동화 도구를 사용해 상세화한 내용입니다. 코드가 변경되면 이 문서도 업데이트해야 합니다.
- 추가로 원하시면:
  - 각 엔드포인트의 예제 요청/응답(샘플 JSON)을 포함
  - 데이터베이스 마이그레이션(Alembic) 설정 가이드 추가
  - 배포 및 환경변수(예: DATABASE_URL, uvicorn 실행 예제) 가이드를 문서에 병합 가능
