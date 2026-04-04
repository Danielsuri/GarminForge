"""
GarminForge Web Application — FastAPI entry point.

Routes
------
GET  /                    Dashboard (workout generator) or login page
POST /auth/login          Handle Garmin Connect credential login
POST /auth/token          Handle base64 token paste
POST /auth/mfa            Handle MFA code submission
GET  /auth/logout         Clear session
POST /workout/generate    Generate workout preview (returns HTML fragment)
POST /workout/upload      Upload generated workout to Garmin Connect

User management and progress routes are in routes_auth.py and routes_my.py.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import secrets
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

# Garmin imports
from garminconnect import Garmin, GarminConnectAuthenticationError

# GarminForge library
from garminforge.auth import TokenStore, _garth
from garminforge.client import GarminForgeClient
from garminforge.exceptions import (
    AuthenticationError,
    TooManyRequestsError,
)

# Web modules
from web.auth_utils import logout_session
from web.db import get_db, init_db
from web.garmin_sso import browser_login, exchange_ticket, make_token_b64, portal_login
from web.models import User
from web.rendering import render_template
from web.routes_auth import router as forge_auth_router
from web.routes_my import router as my_router
from web.translations import SUPPORTED_LANGS
from web.workout_generator import (
    EQUIPMENT_OPTIONS,
    GOALS,
    generate,
    get_available_exercises,
    rebuild_garmin_payload,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# In-process MFA state store (legacy, kept for MFA route).
# ---------------------------------------------------------------------------
_MFA_SESSIONS: dict[str, tuple[Garmin, Any]] = {}

# ---------------------------------------------------------------------------
# Browser login state: login_id → {status, token_b64, error}
# ---------------------------------------------------------------------------
_BROWSER_LOGINS: dict[str, dict] = {}  # type: ignore[type-arg]

# ---------------------------------------------------------------------------
# Server-side token store: token_id (short UUID in session) → token_b64
# Avoids storing the large token in the session cookie.
# Legacy path — new users store tokens in User.garmin_token_b64 via DB.
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


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    init_db()
    _load_remembered_token()
    yield


app = FastAPI(title="GarminForge", docs_url=None, redoc_url=None, lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SECRET_KEY", secrets.token_hex(32)),
    max_age=60 * 60 * 24 * 7,  # 1 week
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Register routers
app.include_router(forge_auth_router)
app.include_router(my_router)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_authenticated(request: Request, db: Session | None = None) -> bool:
    # DB path: check logged-in user's garmin_token_b64
    if db is not None:
        user_id = request.session.get("user_id")
        if user_id:
            user = db.get(User, user_id)
            if user and user.garmin_token_b64:
                return True
    # Legacy path: in-memory token store
    token_id = request.session.get("token_id")
    if token_id and token_id in _TOKEN_STORE:
        return True
    # Auto-attach remembered token if available
    if _REMEMBERED_TOKEN_ID in _TOKEN_STORE:
        request.session["token_id"] = _REMEMBERED_TOKEN_ID
        return True
    return False


def _get_forge_client(request: Request, db: Session | None = None) -> GarminForgeClient:
    # DB path: use user's stored garmin token
    if db is not None:
        user_id = request.session.get("user_id")
        if user_id:
            user = db.get(User, user_id)
            if user and user.garmin_token_b64:
                return GarminForgeClient(
                    TokenStore(token_string=user.garmin_token_b64),
                    inter_call_delay=0.5,
                )
    # Legacy path: in-memory token store
    token_id: str = request.session["token_id"]
    token_b64: str = _TOKEN_STORE[token_id]
    return GarminForgeClient(
        TokenStore(token_string=token_b64),
        inter_call_delay=0.5,
    )


def _store_token(request: Request, token_b64: str, db: Session | None = None) -> None:
    """Save Garmin token — to DB if a GarminForge user is logged in, else to legacy store."""
    if db is not None:
        user_id = request.session.get("user_id")
        if user_id:
            user = db.get(User, user_id)
            if user:
                user.garmin_token_b64 = token_b64
                db.commit()
                return
    # Legacy path: in-memory + disk
    old = request.session.pop("token_id", None)
    if old and old != _REMEMBERED_TOKEN_ID:
        _TOKEN_STORE.pop(old, None)
    _TOKEN_STORE[_REMEMBERED_TOKEN_ID] = token_b64
    request.session["token_id"] = _REMEMBERED_TOKEN_ID
    _save_token_to_disk(token_b64)


def _render(template: str, request: Request, db: Session | None = None, **ctx: Any) -> HTMLResponse:
    return render_template(
        template,
        request,
        authenticated=_is_authenticated(request, db),
        db=db,
        **ctx,
    )


def _error_redirect(request: Request, message: str, back: str = "/") -> RedirectResponse:
    request.session["flash_error"] = message
    return RedirectResponse(back, status_code=303)


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    error: str = "",
    db: Session = Depends(get_db),
):
    flash_error = request.session.pop("flash_error", None) or (error or None)
    flash_success = request.session.pop("flash_success", None)

    return _render(
        "dashboard.html",
        request,
        db=db,
        goals=GOALS,
        equipment_options=EQUIPMENT_OPTIONS,
        flash_error=flash_error,
        flash_success=flash_success,
    )


# ---------------------------------------------------------------------------
# Garmin Connect authentication
# ---------------------------------------------------------------------------


@app.post("/auth/login", response_class=HTMLResponse)
async def auth_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Try headless portal login first; fall back to Playwright browser login."""
    import threading

    # Attempt fast headless login (no browser window)
    try:
        oauth1, oauth2 = portal_login(email, password)
        _store_token(request, make_token_b64(oauth1, oauth2), db)
        request.session["flash_success"] = "Connected to Garmin successfully!"
        return RedirectResponse("/", status_code=303)
    except Exception as exc:
        logger.info("Portal login failed (%s), falling back to browser login.", exc)

    # Fall back to headed Playwright browser
    login_id = str(uuid.uuid4())
    _BROWSER_LOGINS[login_id] = {"status": "pending"}
    request.session["login_id"] = login_id

    def _run() -> None:
        try:
            oauth1, oauth2 = browser_login(email, password)
            _BROWSER_LOGINS[login_id] = {
                "status": "success",
                "token_b64": make_token_b64(oauth1, oauth2),
            }
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
async def auth_finalize(request: Request, db: Session = Depends(get_db)):
    """Called by browser (not fetch) once poll reports success — sets session cookie reliably."""
    login_id = request.session.get("login_id")
    if not login_id or login_id not in _BROWSER_LOGINS:
        return _error_redirect(request, "Login session expired. Please try again.")
    state = _BROWSER_LOGINS.pop(login_id)
    request.session.pop("login_id", None)
    if state["status"] != "success":
        return _error_redirect(request, state.get("error", "Login failed."))
    _store_token(request, state["token_b64"], db)
    request.session["flash_success"] = "Connected to Garmin successfully!"
    return HTMLResponse(
        '<html><body><script>window.location.replace("/")</script></body></html>'
    )


@app.get("/auth/mfa", response_class=HTMLResponse)
async def mfa_page(request: Request):
    if "mfa_key" not in request.session:
        return RedirectResponse("/", status_code=303)
    return _render("mfa.html", request)


@app.post("/auth/mfa", response_class=HTMLResponse)
async def auth_mfa(
    request: Request,
    mfa_code: str = Form(...),
    db: Session = Depends(get_db),
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

    _store_token(request, _garth(client).dumps(), db)
    request.session["flash_success"] = "Logged in successfully!"
    return RedirectResponse("/", status_code=303)


@app.post("/auth/token", response_class=HTMLResponse)
async def auth_token(
    request: Request,
    token_b64: str = Form(...),
    db: Session = Depends(get_db),
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

    _store_token(request, token, db)
    request.session["flash_success"] = "Tokens imported successfully!"
    return RedirectResponse("/", status_code=303)


@app.get("/auth/localtoken")
async def auth_localtoken(request: Request, db: Session = Depends(get_db)):
    """Load tokens from ~/.garminconnect written by garmin_browser_auth.py."""
    import garth as _garth_module

    token_dir = Path.home() / ".garminconnect"
    if not (token_dir / "oauth1_token.json").exists():
        return _error_redirect(
            request,
            "No local tokens found. Run scripts/garmin_browser_auth.py first.",
        )
    try:
        _garth_module.client.load(str(token_dir))
        token_b64 = _garth_module.client.dumps()
        _store_token(request, token_b64, db)
        request.session["flash_success"] = "Loaded tokens from local token store."
    except Exception as exc:
        return _error_redirect(request, f"Failed to load local tokens: {exc}")
    return RedirectResponse("/", status_code=303)


@app.get("/auth/sso", response_class=HTMLResponse)
async def auth_sso(request: Request):
    """Render the embedded Garmin SSO login page."""
    return _render("sso.html", request)


@app.post("/auth/exchange")
async def auth_exchange(
    request: Request,
    ticket: str = Form(...),
    db: Session = Depends(get_db),
):
    """Receive SSO ticket from browser postMessage, exchange for tokens server-side."""
    try:
        oauth1, oauth2 = exchange_ticket(ticket)
        _store_token(request, make_token_b64(oauth1, oauth2), db)
        request.session["flash_success"] = "Connected to Garmin successfully!"
        return {"ok": True}
    except Exception as exc:
        logger.exception("Ticket exchange failed")
        return {"ok": False, "error": str(exc)}


@app.get("/auth/callback", response_class=HTMLResponse)
async def auth_callback(
    request: Request,
    ticket: str = "",
    db: Session = Depends(get_db),
):
    """Garmin redirects the login popup here with ?ticket=ST-..."""
    if not ticket:
        return HTMLResponse(
            "<script>window.opener&&window.opener.location.reload();window.close();</script>"
        )
    try:
        oauth1, oauth2 = exchange_ticket(ticket)
        _store_token(request, make_token_b64(oauth1, oauth2), db)
        request.session["flash_success"] = "Connected to Garmin successfully!"
    except Exception as exc:
        logger.exception("Ticket exchange failed")
        request.session["flash_error"] = f"Login failed: {exc}"
    return HTMLResponse(
        "<script>if(window.opener){window.opener.location.href='/';window.close();}else"
        "{window.location.href='/';}</script>"
    )


@app.get("/auth/cancel")
async def auth_cancel(request: Request):
    login_id = request.session.pop("login_id", None)
    if login_id:
        _BROWSER_LOGINS.pop(login_id, None)
    return RedirectResponse("/", status_code=303)


@app.get("/set-language")
async def set_language(
    request: Request,
    lang: str = "en",
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Save the user's preferred language to their account (if logged in) and session."""
    if lang not in SUPPORTED_LANGS:
        lang = "en"
    request.session["lang"] = lang
    # Persist to DB for logged-in users
    user_id = request.session.get("user_id")
    if user_id:
        user = db.get(User, user_id)
        if user:
            user.preferred_lang = lang
            db.commit()
    back = request.headers.get("referer", "/")
    return RedirectResponse(back, status_code=303)


@app.get("/auth/logout")
async def logout(request: Request):
    _TOKEN_STORE.pop(_REMEMBERED_TOKEN_ID, None)
    try:
        _SAVED_TOKEN_PATH.unlink(missing_ok=True)
    except Exception:
        pass
    logout_session(request)
    request.session.clear()
    return RedirectResponse("/", status_code=303)


# ---------------------------------------------------------------------------
# Workout generation
# ---------------------------------------------------------------------------


@app.get("/debug/workouts")
async def debug_workouts(request: Request, db: Session = Depends(get_db)):
    if not _is_authenticated(request, db):
        return {"error": "not authenticated"}
    forge = _get_forge_client(request, db)
    return forge.get_workouts(start=0, limit=10)


@app.get("/debug/workout/{workout_id}")
async def debug_workout(request: Request, workout_id: int, db: Session = Depends(get_db)):
    if not _is_authenticated(request, db):
        return {"error": "not authenticated"}
    forge = _get_forge_client(request, db)
    return forge.get_workout(workout_id)


@app.get("/debug/lookup/{path:path}")
async def debug_lookup(request: Request, path: str, db: Session = Depends(get_db)):
    """Probe arbitrary connectapi paths. E.g. /debug/lookup/workout-service/equipment"""
    if not _is_authenticated(request, db):
        return {"error": "not authenticated"}
    from garminforge.auth import _garth as _garth_fn

    forge = _get_forge_client(request, db)
    garth = _garth_fn(forge.garmin)
    try:
        return garth.connectapi(f"/{path}")
    except Exception as exc:
        return {"error": str(exc)}


@app.get("/debug/webdata/{path:path}")
async def debug_webdata(request: Request, path: str, db: Session = Depends(get_db)):
    """Fetch connect.garmin.com/web-api/web-data/ static files using garth session."""
    if not _is_authenticated(request, db):
        return {"error": "not authenticated"}
    from garminforge.auth import _garth as _garth_fn

    forge = _get_forge_client(request, db)
    garth = _garth_fn(forge.garmin)
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
    db: Session = Depends(get_db),
):
    if goal not in GOALS:
        return _error_redirect(request, f"Unknown goal: {goal!r}")

    if duration < 15 or duration > 120:
        return _error_redirect(request, "Duration must be between 15 and 120 minutes.")

    try:
        plan = generate(equipment=equipment, goal=goal, duration_minutes=duration)
    except Exception as exc:
        logger.exception("Workout generation failed")
        return _error_redirect(request, f"Generation error: {exc}")

    payload_json = json.dumps(plan.garmin_payload)
    exercises_json = json.dumps([dataclasses.asdict(e) for e in plan.exercises])

    return _render(
        "workout_preview.html",
        request,
        db=db,
        plan=plan,
        payload_json=payload_json,
        exercises_json=exercises_json,
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
    db: Session = Depends(get_db),
):
    if not _is_authenticated(request, db):
        return _error_redirect(request, "Please log in first.")

    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError:
        return _error_redirect(request, "Invalid workout payload.")

    try:
        forge = _get_forge_client(request, db)
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
            "Garmin Connect rate limit hit (429). Wait a minute and try again.",
        )
    except AuthenticationError:
        token_id = request.session.pop("token_id", None)
        if token_id:
            _TOKEN_STORE.pop(token_id, None)
        return _error_redirect(
            request,
            "Authentication failed. Your tokens may have expired. Please log in again.",
        )
    except Exception as exc:
        logger.exception("Upload failed")
        return _error_redirect(request, f"Upload failed: {exc}")


@app.get("/workout/exercises")
async def workout_exercises(
    goal: str = Query(...),
    equipment: list[str] = Query(default=[]),
    muscle_group: str | None = Query(default=None),
    exclude: str | None = Query(default=None),
) -> JSONResponse:
    """Return available exercises for the workout editor (replace / add modals)."""
    if goal not in GOALS:
        return JSONResponse({"error": f"Unknown goal: {goal!r}"}, status_code=400)
    exercises = get_available_exercises(equipment, goal, muscle_group, exclude)
    return JSONResponse(exercises)


@app.post("/workout/rebuild")
async def workout_rebuild(request: Request) -> JSONResponse:
    """Rebuild a Garmin payload from an edited exercises list.

    Body (JSON)::
        {
          "exercises": [...],          # list of ExerciseInfo-shaped dicts
          "goal": "build_muscle",
          "duration_minutes": 45,
          "workout_name": "Build Muscle — 45min (Apr 04)"
        }
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body."}, status_code=400)

    goal = body.get("goal", "")
    if goal not in GOALS:
        return JSONResponse({"error": f"Unknown goal: {goal!r}"}, status_code=400)

    exercises_data = body.get("exercises", [])
    if not isinstance(exercises_data, list) or not exercises_data:
        return JSONResponse({"error": "exercises must be a non-empty list."}, status_code=400)

    duration_minutes = int(body.get("duration_minutes", 45))
    workout_name = str(body.get("workout_name", "Workout"))

    try:
        payload = rebuild_garmin_payload(exercises_data, goal, duration_minutes, workout_name)
    except Exception as exc:
        logger.exception("Payload rebuild failed")
        return JSONResponse({"error": str(exc)}, status_code=500)

    return JSONResponse({"payload_json": json.dumps(payload)})

    return RedirectResponse("/", status_code=303)
