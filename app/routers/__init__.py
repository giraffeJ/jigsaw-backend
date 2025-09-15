# Expose router submodules for easy imports from app.routers
# This module intentionally re-exports specific router modules so callers can do:
#   from app.routers import template_router, user_router, history_router, match_router
# without needing to import each submodule directly.
from . import history_router, match_router, template_router, user_router

__all__ = [
    "template_router",
    "user_router",
    "history_router",
    "match_router",
]
