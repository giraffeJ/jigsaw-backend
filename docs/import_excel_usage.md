엑셀/CSV 매칭 이력(사용자) 임포트 사용법
=====================================

개요
----
프로젝트에는 엑셀(.xlsx/.xls) 또는 CSV 파일로 정리된 사용자 데이터를 DB에 일괄 등록하는 보조 스크립트가 포함되어 있습니다:
- 경로: scripts/import_excel.py

이 문서는 스크립트의 사용법, 입력 데이터(컬럼) 형식, 스크립트가 수행하는 전처리/정규화, 그리고 실행 결과(예상 출력 및 DB 반영)를 단계별로 설명합니다.

사전 준비
--------
- 의존성:
  - pandas, openpyxl (xlsx 지원), xlrd (구형 xls 필요 시)
  - 설치: pip install pandas openpyxl
- 실행 위치:
  - 프로젝트 루트(/home/jeff/git/jigsaw-backend)에서 실행하세요.
- DB:
  - 스크립트는 app.db.SessionLocal을 사용하여 DB에 연결합니다. 필요한 경우 환경변수 DATABASE_URL로 테스트/임시 DB를 지정하세요.

기본 사용법
-----------
- Excel (.xlsx, .xls):
  - python scripts/import_excel.py path/to/file.xlsx --sheet Sheet1
- CSV:
  - python scripts/import_excel.py path/to/file.csv
- 옵션:
  - --sheet: 엑셀 파일의 시트 이름
  - --dry-run: 검증만 수행하고 DB 커밋은 하지 않음
  - --chunk-size: 커밋 배치 사이즈 (기본 1000)

입력 컬럼(헤더)
----------------
스프레드시트의 컬럼 헤더는 가능한 한 Pydantic 스키마 필드 이름과 일치해야 합니다. 스크립트는 EXPECTED_FIELDS를 기준으로 행을 읽어 처리합니다.

필수 권장 컬럼:
- nickname, kakao_id, phone_number, privacy_consent, confidentiality_consent,
- real_name, birth_year, height, residence,
- education_level, final_education, job_title, workplace, workplace_address,
- religion, smoking_status, workplace_matching, preferred_smoking

선택 컬럼:
- referrer_info, mbti, hobbies, additional_info, preferred_religion,
- additional_matching_condition, preferred_age_min, preferred_age_max, preferred_age_range

컬럼명 예시(CSV/Excel 첫 줄):
nickname,kakao_id,phone_number,privacy_consent,confidentiality_consent,real_name,birth_year,height,residence,education_level,final_education,job_title,workplace,workplace_address,religion,smoking_status,preferred_smoking,workplace_matching

데이터 형식 상세
----------------
- Boolean 필드 (privacy_consent, confidentiality_consent)
  - 허용값: True/False, "1"/"0", "예"/"아니오", "yes"/"no" 등 여러 표현을 허용합니다.
  - 파서: 스크립트의 parse_bool()가 다양한 표현을 해석합니다. 파싱 불가능한 경우 기본 False 또는 검증 오류로 처리될 수 있습니다.

- 숫자 필드 (birth_year, height, preferred_age_min, preferred_age_max)
  - Excel에서 종종 float로 읽히므로 정수로 변환을 시도합니다. 변환 실패 시 Pydantic 검증에서 오류가 발생합니다.

- 전화번호 (phone_number)
  - normalize_phone()로 기본적인 정규화 수행:
    - 010xxxxxxxx -> 010-xxxx-xxxx 형식으로 변환 시도
    - 02xxxx.... -> 02-xxxx-xxxx 등, 가능한 경우 하이픈 포함 표준 형태로 포맷
    - Excel에서 선행 0이 제거된 경우(예: "1000000001") heuristics로 0을 붙여 처리 시도

- Enum 필드 (education_level, religion, smoking_status, workplace_matching)
  - 스크립트의 normalize_enum()가 다수의 표현을 허용하여 매칭을 시도합니다.
  - 예: "대졸", "학사" -> EducationLevel.BACHELORS (value "대졸" 기준)
  - workplace_matching: "같은 직장 가능"/"같은 직장 불가능" 형태로 들어가야 하며 다양한 변형을 허용합니다.
  - 실패 시 Pydantic 검증에서 오류가 발생합니다.

- 복수 선택(콤마 등으로 구분) 필드
  - preferred_smoking, preferred_religion 등은 CSV 문자열(예: "비흡연,전자담배") 또는 구분자로 분리된 값들을 허용합니다.
  - 스크립트는 토큰별로 normalize_enum을 적용하여 최종적으로 CSV 형태의 문자열로 저장합니다.

preferred_age_range 대응
------------------------
- 이전 스키마 호환을 위해 preferred_age_range 같은 필드가 입력될 수 있으나,
  현재 스키마는 preferred_age_min / preferred_age_max (출생연도, 4자리) 필드를 선호합니다.
- 스프레드시트에 min/max 가 제공되면 스크립트는 이를 우선 사용합니다.

중복 처리
--------
- 스크립트는 파일 내의 kakao_id 또는 phone_number 필드를 기준으로 DB 내 중복을 검사합니다.
- 이미 DB에 존재하는 kakao_id 또는 phone_number가 발견되면 해당 행은 건너뜁니다(스킵).
- 동일 파일 내에서 중복이 발생하지 않도록 existing_kakao/phone 집합으로 방지합니다.

전처리 및 정규화 요약
--------------------
- 전화번호 정규화(normalize_phone)
- Enum 값 유연 매칭(normalize_enum)
- preferred_smoking / preferred_religion: 토큰화 후 각 토큰을 enum으로 정규화하여 CSV로 저장
- 날짜/숫자 필드: float->int 변환 시도
- datetime 타입 셀: ISO 문자열로 변환

실행 결과(예상 출력)
------------------
스크립트는 실행 후 요약을 출력합니다:
- Total rows in file: N
- Inserted (or Would insert if --dry-run): M
- Skipped due to duplicates: K
- Validation errors: E

Validation errors가 있을 경우:
- 각 오류의 예시(최대 10개)를 출력합니다.
- 오류 메시지는 Pydantic validation 에러 또는 enum 변환 실패 등 다양한 원인을 포함합니다.

예: dry-run 검증
----------------
- 변경 없이 검증만 수행하려면:
  python scripts/import_excel.py data.xlsx --sheet Sheet1 --dry-run

- 출력 예:
  Import summary:
    Total rows in file: 10
    Would insert (dry-run): 8
    Skipped due to duplicates: 1
    Validation errors: 1
    Examples of validation errors (first 10):
      {'row': 5, 'error': "Enum conversion failed or missing for field 'religion'"}

문제 해결(트러블슈팅)
--------------------
- Missing required columns: 스크립트가 필수 컬럼(nickname/kakao_id/phone_number 등)을 찾지 못하면 실행을 중단하고 컬럼 목록을 출력합니다. 스프레드시트의 헤더를 정확한 필드명으로 수정하세요.
- Enum 변환 실패: 입력값이 프로젝트의 enum 값(예: "흡연"/"비흡연"/"전자담배")과 매핑되지 않으면 에러가 발생합니다. normalize_enum()가 여러 변형을 시도하지만, 필요시 스프레드시트에서 값을 enum value로 맞춰주세요.
- Excel이 숫자를 float로 읽음: birth_year, height 등은 int로 변환됩니다. 소수점이 섞여있으면 (예: "1990.0") 정상 처리되지만 비숫자 값은 오류를 유발합니다.

DB 확인
-------
- 실제 삽입 후 DB의 users 테이블을 확인하여 새 레코드가 들어갔는지 검증하세요.
- 테스트 환경에서 먼저 --dry-run으로 확인한 뒤 커밋 실행을 권장합니다.

개발자 팁
---------
- 대량 삽입 전에 --dry-run으로 스키마/enum/전화번호 정규화가 의도대로 동작하는지 확인하세요.
- 엑셀의 자동 포맷(날짜/숫자)에 의해 값이 변형될 수 있으므로, 중요한 식별자(kakao_id, phone_number)는 텍스트 형식으로 지정하는 것이 안전합니다.
- 스크립트는 간단한 정규화/허용 변환을 포함하지만, 특수한 기업명 표기 등은 수작업 전처리가 필요할 수 있습니다.

예시 CSV(한 줄)
----------------
nickname,kakao_id,phone_number,privacy_consent,confidentiality_consent,real_name,birth_year,height,residence,education_level,final_education,job_title,workplace,workplace_address,religion,smoking_status,preferred_smoking,workplace_matching
홍길동,hong_123,010-1234-5678,예,예,홍길동,1992,178,서울,대졸,테스트대학,개발자,주식회사 ABC,서울,무교,비흡연,비흡연,같은 직장 가능

결론
----
scripts/import_excel.py는 실무에서 스프레드시트로 수집한 사용자 데이터를 DB에 안전하게 반영하기 위한 도구입니다. 대량 처리 시에는 --dry-run으로 우선 검증하고, 필요하다면 스프레드시트 내의 값들을 enum 값과 맞추어 사전 정제한 뒤 실제 커밋을 수행하세요.
