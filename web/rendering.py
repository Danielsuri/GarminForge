"""
Shared Jinja2 template renderer used by app.py and the route modules.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from web.translations import SUPPORTED_LANGS, make_t

_BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=_BASE_DIR / "templates")


def _detect_version() -> str:
    version_file = _BASE_DIR.parent / "VERSION"
    try:
        v = version_file.read_text().strip()
        if v:
            return v
    except Exception:
        pass
    return "dev"


APP_VERSION: str = _detect_version()


def render_template(
    template: str,
    request: Request,
    *,
    authenticated: bool = False,
    db: Session | None = None,
    **ctx: object,
) -> HTMLResponse:
    """Render a Jinja2 template, injecting ``authenticated``, ``forge_user``,
    flash messages, and language helpers (``lang``, ``t``).

    Language priority: DB user preference > session > default "en".
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

    # Resolve language: DB preference beats session, then fallback to "en".
    lang: str = "en"
    if forge_user is not None and forge_user.preferred_lang in SUPPORTED_LANGS:
        lang = forge_user.preferred_lang  # type: ignore[assignment]
    else:
        raw = request.session.get("lang", "en")
        if raw in SUPPORTED_LANGS:
            lang = raw

    # Auto-pop flash messages unless the caller already passed them
    if "flash_error" not in ctx:
        ctx["flash_error"] = request.session.pop("flash_error", None)
    if "flash_success" not in ctx:
        ctx["flash_success"] = request.session.pop("flash_success", None)

    return templates.TemplateResponse(
        request,
        template,
        {"authenticated": authenticated, "forge_user": forge_user, "lang": lang, "t": make_t(lang), "app_version": APP_VERSION, **ctx},
    )
