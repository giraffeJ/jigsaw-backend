from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app import models
from app.services import matching as _matching


class MatchService:
    """읽기 전용 매칭 서비스 헬퍼.

    사용법: MatchService(user_manager, history_manager, template_manager)

    이 서비스는 아래와 같은 매니저 API를 사용한다고 가정합니다:
        - user_manager.get_by_id(db, id) -> Optional[User]
        - user_manager.get_by_nickname(db, nickname) -> Optional[User]
        - user_manager.list(db, filters=..., skip=0, limit=...)
        - matching.mutual_candidates 기반의 히스토리/매칭 유틸리티
        - template_manager.get_by_id(db, id) -> Optional[Template]

    주의:
        이 서비스의 메서드는 기본적으로 읽기 전용이며 데이터베이스에 영구적인 쓰기를 수행하지 않아야 합니다.
    """

    def __init__(self, user_manager, history_manager, template_manager):
        self.user_manager = user_manager
        self.history_manager = history_manager
        self.template_manager = template_manager

    def get_template_for_id_1(self, db: Session) -> models.Template:
        """id == 1인 템플릿을 반환합니다.

        Args:
            db (Session): SQLAlchemy 세션.

        Returns:
            models.Template: id가 1인 템플릿 인스턴스.

        Raises:
            ValueError: 템플릿(id=1)을 찾지 못하면 발생(404와 유사).
        """
        tmpl = None
        # Prefer manager method if available
        getter = getattr(self.template_manager, "get_by_id", None)
        if callable(getter):
            tmpl = getter(db, 1)
        else:
            # Fallback: try crud-style function name
            from app import crud

            tmpl = (
                crud.get_template(db, key="default", version=1)
                if hasattr(crud, "get_template")
                else None
            )

        if not tmpl:
            raise ValueError("template id=1 not found")
        return tmpl

    def single_match(
        self, db: Session, *, user_id: Optional[int] = None, nickname: Optional[str] = None
    ) -> List[Tuple[models.User, int]]:
        """단일 대상 사용자를 위한 후보자 목록을 찾습니다.

        Args:
            db (Session): SQLAlchemy 세션.
            user_id (Optional[int]): 대상 사용자 ID (nickname과 상호 배타적).
            nickname (Optional[str]): 대상 사용자 닉네임 (user_id와 상호 배타적).

        Returns:
            List[Tuple[models.User, int]]: (candidate_user, score) 튜플의 정렬된 목록.
                낮은 score가 더 선호되는 후보를 의미합니다 (presented_count 기준).

        Raises:
            ValueError: user_id와 nickname이 모두 제공되지 않았거나 대상 사용자를 찾을 수 없을 때 발생.

        Notes:
            - 이 메서드는 읽기 전용이며 DB 쓰기를 수행하지 않습니다.
            - 내부적으로 matching.mutual_candidates를 사용합니다.
        """
        if user_id is None and nickname is None:
            raise ValueError("either user_id or nickname must be provided")

        # Resolve subject user
        subject = None
        if user_id is not None:
            getter = getattr(self.user_manager, "get_by_id", None)
            if callable(getter):
                subject = getter(db, user_id)
        if subject is None and nickname is not None:
            getter_n = getattr(self.user_manager, "get_by_nickname", None)
            if callable(getter_n):
                subject = getter_n(db, nickname)
        if subject is None:
            raise ValueError("subject user not found")

        # Use existing mutual_candidates logic to produce filtered & scored candidate list.
        # cooldown_days=0 by default here (caller may filter earlier). Limit reasonably large.
        cand_meta = _matching.mutual_candidates(db, requester=subject, cooldown_days=0, limit=1000)

        out: List[Tuple[models.User, int]] = []
        for m in cand_meta:
            cand_id = m.get("candidate_id")
            # fetch user object via manager
            cand = None
            getter = getattr(self.user_manager, "get_by_id", None)
            if callable(getter):
                cand = getter(db, cand_id)
            if cand is None:
                # skip if user record missing
                continue
            score = int(m.get("presented_count", 0))
            out.append((cand, score))

        # mutual_candidates already sorts by presented_count asc, last_presented, -score
        # but ensure sorting stability here by score ascending
        out.sort(key=lambda x: (x[1], x[0].id))
        return out

    def bulk_match(self, db: Session) -> List[Tuple[models.User, Optional[models.User]]]:
        """그리디 방식의 벌크 1:1 유사 추천을 생성합니다.

        각 활성 사용자(subject)에 대해 single_match에서의 우선순위에 따라
        아직 할당되지 않은 최상위 후보를 추천합니다. 후보가 없으면 None을 할당합니다.

        Args:
            db (Session): SQLAlchemy 세션.

        Returns:
            List[Tuple[models.User, Optional[models.User]]]: (subject_user, recommended_candidate_or_None) 목록.

        Notes:
            - 읽기 전용: DB에 쓰지 않습니다.
            - 필요한 매니저 API가 없을 경우 app.crud로 폴백합니다.
        """
        # list active users via user_manager.list(filters={"is_active": True}, limit=...)
        list_fn = getattr(self.user_manager, "list", None)
        if not callable(list_fn):
            # fallback to crud
            from app import crud

            users = crud.get_users(db, skip=0, limit=10000)
        else:
            users = list_fn(db, filters={"is_active": True}, skip=0, limit=10000)

        assignments = []
        assigned_candidate_ids = set()

        # Iterate subjects in deterministic order (by id) to keep results stable
        users_sorted = sorted(users, key=lambda u: u.id)
        for subject in users_sorted:
            try:
                cands = self.single_match(db, user_id=subject.id)
            except Exception:
                cands = []
            recommended = None
            for cand_user, score in cands:
                if cand_user.id not in assigned_candidate_ids:
                    recommended = cand_user
                    assigned_candidate_ids.add(cand_user.id)
                    break
            assignments.append((subject, recommended))

        return assignments

    def fill_template(self, template_content: str, profile_url: str) -> str:
        """템플릿 내용 내 ``{url}`` 플레이스홀더를 제공된 profile_url로 치환합니다.

        Args:
            template_content (str): ``{url}``를 포함할 수 있는 템플릿 문자열.
            profile_url (str): 템플릿에 삽입할 프로필 URL.

        Returns:
            str: 치환된 템플릿 문자열. template_content가 None이거나 치환 중 예외가 발생하면 원본을 반환합니다.
        """
        if template_content is None:
            return template_content
        try:
            return template_content.replace("{url}", profile_url)
        except Exception:
            return template_content
