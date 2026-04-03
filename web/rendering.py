"""
Shared Jinja2 template renderer used by app.py and the route modules.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

_BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=_BASE_DIR / "templates")


def render_template(
    template: str,
    request: Request,
    *,
    authenticated: bool = False,
    db: Session | None = None,
    **ctx: object,
) -> HTMLResponse:
    """Render a Jinja2 template, injecting `authenticated`, `forge_user`, and flash messages.

    Flash messages are auto-popped from the session so they display once even
    when the caller doesn't pull them manually (e.g. after a redirect into a
    route that doesn't know about the flash).  Callers that already popped and
    passed flash values explicitly take precedence.
    """
    forge_user = None
    if db is not None:
        from web.auth_utils import get_current_user

        forge_user = get_current_user(request, db)

    # Auto-detect Garmin auth from DB user when not explicitly provided.
    # Routes in routes_my.py don't have access to app.py's _is_authenticated,
    # but the user's garmin_token_b64 column is the source of truth for DB users.
    if not authenticated and forge_user is not None:
        authenticated = bool(forge_user.garmin_token_b64)

    # Auto-pop flash messages unless the caller already passed them
    if "flash_error" not in ctx:
        ctx["flash_error"] = request.session.pop("flash_error", None)
    if "flash_success" not in ctx:
        ctx["flash_success"] = request.session.pop("flash_success", None)

    return templates.TemplateResponse(
        request,
        template,
        {"authenticated": authenticated, "forge_user": forge_user, **ctx},
    )
