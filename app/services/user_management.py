"""사용자 관리 유틸리티

코드베이스 전반에서 유용한 사용자 관련 헬퍼 함수들을 포함합니다.
유지보수성과 테스트 용이성을 위해 별도 모듈로 분리되어 있습니다.

현재 제공 함수:
- normalize_workplace(s: str) -> str
"""

from typing import Optional


def normalize_workplace(s: Optional[str]) -> str:
    """직장/회사 문자열을 비교하기 쉽게 정규화합니다.

    동작:
    - 입력을 소문자로 변환합니다.
    - "㈜", "(주)", "주식회사" 등 한국의 일반적인 법인 표기 및 괄호 표기를 제거합니다.
    - 영숫자나 공백이 아닌 문자는 모두 제거합니다.
    - 연속된 공백을 하나로 축약합니다.
    - falsy(예: None, 빈 문자열) 입력의 경우 빈 문자열을 반환합니다.
    """
    if not s:
        return ""
    s2 = s.lower()
    for token in ["㈜", "(주)", "주식회사", "주)", "주(", "주식", "주."]:
        s2 = s2.replace(token, " ")
    s2 = "".join(ch for ch in s2 if ch.isalnum() or ch.isspace())
    s2 = " ".join(s2.split())
    return s2.strip()
