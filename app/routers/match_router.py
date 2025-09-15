# Lightweight adapter that re-exports the working `match` module's router.
# main.py expects `match_router.router`. Forward to the existing module to avoid duplication.
from . import match as match

router = match.router

__all__ = ["router"]
