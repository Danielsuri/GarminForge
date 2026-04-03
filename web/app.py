"""
GarminForge Web Application — FastAPI entry point.

Routes
------
GET  /                    Dashboard (workout generator) or login page
POST /auth/login          Handle credential login
POST /auth/token          Handle base64 token paste
POST /auth/mfa            Handle MFA code submission
GET  /auth/logout         Clear session
POST /workout/generate    Generate workout preview (returns HTML fragment)
POST /workout/upload      Upload generated workout to Garmin Connect
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

# Garmin imports
from garminconnect import Garmin, GarminConnectAuthenticationError

# GarminForge library
from garminforge.auth import TokenStore, with_backoff, _garth
from garminforge.client import GarminForgeClient
from garminforge.exceptions import (
    AuthenticationError,
    TooManyRequestsError,
    TokenNotFoundError,
)

# Web modules
from web.workout_generator import GOALS, EQUIPMENT_OPTIONS, generate
from web.garmin_sso import exchange_ticket, browser_login, portal_login, make_token_b64

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent

app = FastAPI(title="GarminForge", docs_url=None, redoc_url=None)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SECRET_KEY", secrets.token_hex(32)),
    max_age=60 * 60 * 24 * 7,  # 1 week
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# ---------------------------------------------------------------------------
# In-process MFA state store (legacy, kept for MFA route).
# ---------------------------------------------------------------------------
_MFA_SESSIONS: dict[str, tuple[Garmin, Any]] = {}

# ---------------------------------------------------------------------------
# Browser login state: login_id → {status, token_b64, error}
# ---------------------------------------------------------------------------
_BROWSER_LOGINS: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# Server-side token store: token_id (short UUID in session) → token_b64
# Avoids storing the large token in the session cookie.
# ---------------------------------------------------------------------------
_TOKEN_STORE: dict[str, str] = {}

_SAVED_TOKEN_PATH = Path.home() / ".garminforge_token"
_REMEMBERED_TOKEN_ID = "remembered"


def _save_token_to_disk(token_b64: str) -> None:
    try:
        _SAVED_TOKEN_PATH.write_text(token_b64, encoding="utf-8")
        _SAVED_TOKEN_PATH.chmod(0o600)
    except Exception as exc:
        logger.warning("Could not save token to disk: %s", exc)


def _load_remembered_token() -> bool:
    """Load saved token from disk into the store. Returns True if loaded."""
    if not _SAVED_TOKEN_PATH.exists():
        return False
    try:
        token_b64 = _SAVED_TOKEN_PATH.read_text(encoding="utf-8").strip()
        if token_b64:
            _TOKEN_STORE[_REMEMBERED_TOKEN_ID] = token_b64
            return True
    except Exception as exc:
        logger.warning("Could not load saved token: %s", exc)
    return False


# Load saved token at startup
_load_remembered_token()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_authenticated(request: Request) -> bool:
    token_id = request.session.get("token_id")
    if token_id and token_id in _TOKEN_STORE:
        return True
    # Auto-attach remembered token if available
    if _REMEMBERED_TOKEN_ID in _TOKEN_STORE:
        request.session["token_id"] = _REMEMBERED_TOKEN_ID
        return True
    return False


def _get_forge_client(request: Request) -> GarminForgeClient:
    token_id: str = request.session["token_id"]
    token_b64: str = _TOKEN_STORE[token_id]
    return GarminForgeClient(
        TokenStore(token_string=token_b64),
        inter_call_delay=0.5,
    )


def _store_token(request: Request, token_b64: str) -> None:
    """Save token server-side, persist to disk, and put its ID in the session cookie."""
    old = request.session.pop("token_id", None)
    if old and old != _REMEMBERED_TOKEN_ID:
        _TOKEN_STORE.pop(old, None)
    _TOKEN_STORE[_REMEMBERED_TOKEN_ID] = token_b64
    request.session["token_id"] = _REMEMBERED_TOKEN_ID
    _save_token_to_disk(token_b64)


def _render(template: str, request: Request, **ctx) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        template,
        {"authenticated": _is_authenticated(request), **ctx},
    )


def _error_redirect(request: Request, message: str, back: str = "/") -> RedirectResponse:
    request.session["flash_error"] = message
    return RedirectResponse(back, status_code=303)


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, error: str = ""):
    flash_error = request.session.pop("flash_error", None) or (error or None)
    flash_success = request.session.pop("flash_success", None)

    if not _is_authenticated(request):
        return _render("index.html", request,
                        flash_error=flash_error,
                        flash_success=flash_success)

    return _render("dashboard.html", request,
                   goals=GOALS,
                   equipment_options=EQUIPMENT_OPTIONS,
                   flash_error=flash_error,
                   flash_success=flash_success)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

@app.post("/auth/login", response_class=HTMLResponse)
async def auth_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    """Try headless portal login first; fall back to Playwright browser login."""
    import threading

    # Attempt fast headless login (no browser window)
    try:
        oauth1, oauth2 = portal_login(email, password)
        _store_token(request, make_token_b64(oauth1, oauth2))
        request.session["flash_success"] = "Connected to Garmin successfully!"
        return RedirectResponse("/", status_code=303)
    except Exception as exc:
        logger.info("Portal login failed (%s), falling back to browser login.", exc)

    # Fall back to headed Playwright browser
    login_id = str(uuid.uuid4())
    _BROWSER_LOGINS[login_id] = {"status": "pending"}
    request.session["login_id"] = login_id

    def _run():
        try:
            oauth1, oauth2 = browser_login(email, password)
            _BROWSER_LOGINS[login_id] = {"status": "success", "token_b64": make_token_b64(oauth1, oauth2)}
        except Exception as exc:
            _BROWSER_LOGINS[login_id] = {"status": "error", "error": str(exc)}

    threading.Thread(target=_run, daemon=True).start()
    return RedirectResponse("/auth/waiting", status_code=303)


@app.get("/auth/waiting", response_class=HTMLResponse)
async def auth_waiting(request: Request):
    return _render("waiting.html", request)


@app.get("/auth/poll")
async def auth_poll(request: Request):
    login_id = request.session.get("login_id")
    if not login_id or login_id not in _BROWSER_LOGINS:
        return {"status": "error", "error": "No login in progress."}
    state = _BROWSER_LOGINS[login_id]
    if state["status"] == "error":
        logger.error("Browser login failed: %s", state.get("error"))
    return {"status": state["status"], "error": state.get("error", "")}


@app.get("/auth/finalize")
async def auth_finalize(request: Request):
    """Called by browser (not fetch) once poll reports success — sets session cookie reliably."""
    login_id = request.session.get("login_id")
    if not login_id or login_id not in _BROWSER_LOGINS:
        return _error_redirect(request, "Login session expired. Please try again.")
    state = _BROWSER_LOGINS.pop(login_id)
    request.session.pop("login_id", None)
    if state["status"] != "success":
        return _error_redirect(request, state.get("error", "Login failed."))
    _store_token(request, state["token_b64"])
    request.session["flash_success"] = "Connected to Garmin successfully!"
    return HTMLResponse('<html><body><script>window.location.replace("/")</script></body></html>')


@app.get("/auth/mfa", response_class=HTMLResponse)
async def mfa_page(request: Request):
    if "mfa_key" not in request.session:
        return RedirectResponse("/", status_code=303)
    return _render("mfa.html", request)


@app.post("/auth/mfa", response_class=HTMLResponse)
async def auth_mfa(
    request: Request,
    mfa_code: str = Form(...),
):
    mfa_key = request.session.pop("mfa_key", None)
    if not mfa_key or mfa_key not in _MFA_SESSIONS:
        return _error_redirect(request, "MFA session expired. Please log in again.")

    client, state = _MFA_SESSIONS.pop(mfa_key)
    try:
        client.resume_login(state, mfa_code.strip())
    except GarminConnectAuthenticationError:
        return _error_redirect(request, "Invalid MFA code. Please try again.")
    except Exception as exc:
        return _error_redirect(request, f"MFA error: {exc}")

    _store_token(request, _garth(client).dumps())
    request.session["flash_success"] = "Logged in successfully!"
    return RedirectResponse("/", status_code=303)


@app.post("/auth/token", response_class=HTMLResponse)
async def auth_token(
    request: Request,
    token_b64: str = Form(...),
):
    """Accept a base64 token string (from garth.dumps())."""
    token = token_b64.strip()
    if not token:
        return _error_redirect(request, "Token string cannot be empty.")

    # Validate by attempting to load it
    try:
        store = TokenStore(token_string=token)
        garmin = Garmin()
        store.load(garmin)
    except AuthenticationError as exc:
        return _error_redirect(request, f"Invalid token: {exc}")
    except Exception as exc:
        return _error_redirect(request, f"Token error: {exc}")

    _store_token(request, token)
    request.session["flash_success"] = "Tokens imported successfully!"
    return RedirectResponse("/", status_code=303)


@app.get("/auth/localtoken")
async def auth_localtoken(request: Request):
    """Load tokens from ~/.garminconnect written by garmin_browser_auth.py."""
    import garth as _garth_module
    token_dir = Path.home() / ".garminconnect"
    if not (token_dir / "oauth1_token.json").exists():
        return _error_redirect(request, "No local tokens found. Run scripts/garmin_browser_auth.py first.")
    try:
        _garth_module.client.load(str(token_dir))
        token_b64 = _garth_module.client.dumps()
        _store_token(request, token_b64)
        request.session["flash_success"] = "Loaded tokens from local token store."
    except Exception as exc:
        return _error_redirect(request, f"Failed to load local tokens: {exc}")
    return RedirectResponse("/", status_code=303)


@app.get("/auth/sso", response_class=HTMLResponse)
async def auth_sso(request: Request):
    """Render the embedded Garmin SSO login page."""
    return _render("sso.html", request)


@app.post("/auth/exchange")
async def auth_exchange(request: Request, ticket: str = Form(...)):
    """Receive SSO ticket from browser postMessage, exchange for tokens server-side."""
    try:
        oauth1, oauth2 = exchange_ticket(ticket)
        _store_token(request, make_token_b64(oauth1, oauth2))
        request.session["flash_success"] = "Connected to Garmin successfully!"
        return {"ok": True}
    except Exception as exc:
        logger.exception("Ticket exchange failed")
        return {"ok": False, "error": str(exc)}


@app.get("/auth/callback", response_class=HTMLResponse)
async def auth_callback(request: Request, ticket: str = ""):
    """Garmin redirects the login popup here with ?ticket=ST-..."""
    import base64 as _b64
    import json as _json
    if not ticket:
        return HTMLResponse("<script>window.opener&&window.opener.location.reload();window.close();</script>")
    try:
        oauth1, oauth2 = exchange_ticket(ticket)
        _store_token(request, make_token_b64(oauth1, oauth2))
        request.session["flash_success"] = "Connected to Garmin successfully!"
    except Exception as exc:
        logger.exception("Ticket exchange failed")
        request.session["flash_error"] = f"Login failed: {exc}"
    return HTMLResponse(
        "<script>if(window.opener){window.opener.location.href='/';window.close();}else{window.location.href='/';}</script>"
    )


@app.get("/auth/cancel")
async def auth_cancel(request: Request):
    login_id = request.session.pop("login_id", None)
    if login_id:
        _BROWSER_LOGINS.pop(login_id, None)
    return RedirectResponse("/", status_code=303)


@app.get("/auth/logout")
async def logout(request: Request):
    _TOKEN_STORE.pop(_REMEMBERED_TOKEN_ID, None)
    try:
        _SAVED_TOKEN_PATH.unlink(missing_ok=True)
    except Exception:
        pass
    request.session.clear()
    return RedirectResponse("/", status_code=303)


# ---------------------------------------------------------------------------
# Workout generation
# ---------------------------------------------------------------------------

@app.get("/debug/workouts")
async def debug_workouts(request: Request):
    if not _is_authenticated(request):
        return {"error": "not authenticated"}
    forge = _get_forge_client(request)
    return forge.get_workouts(start=0, limit=10)


@app.get("/debug/workout/{workout_id}")
async def debug_workout(request: Request, workout_id: int):
    if not _is_authenticated(request):
        return {"error": "not authenticated"}
    forge = _get_forge_client(request)
    return forge.get_workout(workout_id)


@app.get("/debug/lookup/{path:path}")
async def debug_lookup(request: Request, path: str):
    """Probe arbitrary connectapi paths. E.g. /debug/lookup/workout-service/equipment"""
    if not _is_authenticated(request):
        return {"error": "not authenticated"}
    from garminforge.auth import _garth
    forge = _get_forge_client(request)
    garth = _garth(forge.garmin)
    try:
        return garth.connectapi(f"/{path}")
    except Exception as exc:
        return {"error": str(exc)}


@app.get("/debug/webdata/{path:path}")
async def debug_webdata(request: Request, path: str):
    """Fetch connect.garmin.com/web-api/web-data/ static files using garth session."""
    if not _is_authenticated(request):
        return {"error": "not authenticated"}
    from garminforge.auth import _garth
    import json as _json
    forge = _get_forge_client(request)
    garth = _garth(forge.garmin)
    r = garth.request("GET", "connect", f"/web-api/web-data/{path}", api=False)
    try:
        return r.json()
    except Exception:
        return {"text": r.text[:2000]}


@app.post("/workout/generate", response_class=HTMLResponse)
async def workout_generate(
    request: Request,
    goal: str = Form(...),
    duration: int = Form(...),
    equipment: list[str] = Form(default=[]),
):
    if not _is_authenticated(request):
        return _error_redirect(request, "Please log in first.")

    if goal not in GOALS:
        return _error_redirect(request, f"Unknown goal: {goal!r}")

    if duration < 15 or duration > 120:
        return _error_redirect(request, "Duration must be between 15 and 120 minutes.")

    try:
        plan = generate(equipment=equipment, goal=goal, duration_minutes=duration)
    except Exception as exc:
        logger.exception("Workout generation failed")
        return _error_redirect(request, f"Generation error: {exc}")

    # Serialise payload for the hidden form field
    payload_json = json.dumps(plan.garmin_payload)

    return _render(
        "workout_preview.html",
        request,
        plan=plan,
        payload_json=payload_json,
        goals=GOALS,
        equipment_options=EQUIPMENT_OPTIONS,
        selected_goal=goal,
        selected_duration=duration,
        selected_equipment=equipment,
    )


@app.post("/workout/upload", response_class=HTMLResponse)
async def workout_upload(
    request: Request,
    payload_json: str = Form(...),
    schedule_date: str = Form(default=""),
):
    if not _is_authenticated(request):
        return _error_redirect(request, "Please log in first.")

    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError:
        return _error_redirect(request, "Invalid workout payload.")

    try:
        forge = _get_forge_client(request)
        result = forge.upload_workout(payload)
        workout_id = result.get("workoutId") or result.get("workout", {}).get("workoutId")

        scheduled_on = None
        if schedule_date and workout_id:
            forge.schedule_workout(workout_id, schedule_date)
            scheduled_on = schedule_date

        request.session["flash_success"] = (
            f"Workout \"{payload.get('workoutName')}\" uploaded to Garmin Connect!"
            + (f" Scheduled for {scheduled_on}." if scheduled_on else "")
        )

    except TooManyRequestsError:
        return _error_redirect(
            request,
            "Garmin Connect rate limit hit (429). Wait a minute and try again."
        )
    except AuthenticationError:
        token_id = request.session.pop("token_id", None)
        if token_id:
            _TOKEN_STORE.pop(token_id, None)
        return _error_redirect(
            request,
            "Authentication failed. Your tokens may have expired. Please log in again."
        )
    except Exception as exc:
        logger.exception("Upload failed")
        return _error_redirect(request, f"Upload failed: {exc}")

    return RedirectResponse("/", status_code=303)
