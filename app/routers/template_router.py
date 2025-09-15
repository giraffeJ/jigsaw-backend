# Lightweight adapter that re-exports the working `templates` module's router.
# Some historical files in this package used different names; main.py expects
# `template_router.router`. To avoid duplicating code, forward to the existing module.
from . import templates as templates

router = templates.router

__all__ = ["router"]
