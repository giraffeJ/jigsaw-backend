from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from jinja2 import Environment, StrictUndefined

from app import models

_env = Environment(
    autoescape=False, undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True
)


def _age_from_birth_year(birth_year: Optional[int]) -> Optional[int]:
    if not birth_year:
        return None
    # 만 나이 근사: 올해 기준
    return datetime.utcnow().year - birth_year


def default_params(requester: models.User, candidate: models.User) -> Dict[str, Any]:
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
    tmpl = _env.from_string(template_str)
    return tmpl.render(**params)
