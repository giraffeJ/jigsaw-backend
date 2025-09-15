"""템플릿 엔진 헬퍼

Jinja2 환경을 사용해 템플릿 문자열을 렌더링하는 간단한 유틸리티를 제공합니다.
주로 매칭용 템플릿에서 사용되는 기본 파라미터 생성 및 문자열 렌더링을 담당합니다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from jinja2 import Environment, StrictUndefined

from app import models

_env = Environment(
    autoescape=False, undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True
)


def _age_from_birth_year(birth_year: Optional[int]) -> Optional[int]:
    """출생연도로부터 만 나이(근사)를 계산합니다.

    Args:
        birth_year (Optional[int]): 사용자의 출생연도(년). None 또는 falsy 값이면 None을 반환합니다.

    Returns:
        Optional[int]: 계산된 나이(정수) 또는 입력이 없으면 None.
    """
    if not birth_year:
        return None
    # 만 나이 근사: 올해 기준
    return datetime.utcnow().year - birth_year


def default_params(requester: models.User, candidate: models.User) -> Dict[str, Any]:
    """템플릿 렌더링에 사용할 기본 파라미터 딕셔너리를 생성합니다.

    Args:
        requester (models.User): 추천을 요청하는 사용자 모델 인스턴스.
        candidate (models.User): 추천 대상 사용자 모델 인스턴스.

    Returns:
        Dict[str, Any]: 템플릿에서 사용 가능한 기본 키-값 매핑.
    """
    return {
        "requester_nick": requester.nickname,
        "candidate_nick": candidate.nickname,
        "requester_age": _age_from_birth_year(requester.birth_year),
        "candidate_age": _age_from_birth_year(candidate.birth_year),
        "requester_height": requester.height,
        "candidate_height": candidate.height,
        "requester_region": requester.residence,
        "candidate_region": candidate.residence,
        "requester_job": requester.job_title,
        "candidate_job": candidate.job_title,
    }


def render_string(template_str: str, params: Dict[str, Any]) -> str:
    """Jinja2 템플릿 문자열을 주어진 파라미터로 렌더링합니다.

    Args:
        template_str (str): Jinja2 템플릿 표현을 포함한 문자열.
        params (Dict[str, Any]): 템플릿 렌더링에 사용될 매핑(딕셔너리).

    Returns:
        str: 렌더링된 문자열 결과.
    """
    tmpl = _env.from_string(template_str)
    return tmpl.render(**params)
