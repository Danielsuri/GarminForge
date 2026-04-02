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
from garminforge.auth import TokenStore, with_backoff
from garminforge.client import GarminForgeClient
from garminforge.exceptions import (
    AuthenticationError,
    TooManyRequestsError,
    TokenNotFoundError,
)

# Web modules
from web.workout_generator import GOALS, EQUIPMENT_OPTIONS, generate

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
# In-process MFA state store.
# Maps a random key → (Garmin instance, garth OAuth state).
# Not suitable for multi-process deployments (use Redis for that).
# ---------------------------------------------------------------------------
_MFA_SESSIONS: dict[str, tuple[Garmin, Any]] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_authenticated(request: Request) -> bool:
    return bool(request.session.get("token_b64"))


def _get_forge_client(request: Request) -> GarminForgeClient:
    token_b64: str = request.session["token_b64"]
    return GarminForgeClient(
        TokenStore(token_string=token_b64),
        inter_call_delay=0.5,
    )


def _render(template: str, request: Request, **ctx) -> HTMLResponse:
    return templates.TemplateResponse(
        template,
        {"request": request, "authenticated": _is_authenticated(request), **ctx},
    )


def _error_redirect(request: Request, message: str, back: str = "/") -> RedirectResponse:
    request.session["flash_error"] = message
    return RedirectResponse(back, status_code=303)


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    flash_error = request.session.pop("flash_error", None)
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
    """Attempt credentials login.  Handles MFA via two-step flow."""
    try:
        client = Garmin(email=email, password=password, return_on_mfa=True)
        result = client.login()
    except GarminConnectAuthenticationError as exc:
        return _error_redirect(
            request,
            f"Login failed: {exc}.  "
            "Note: Garmin's SSO has been broken since March 2026 — "
            "use 'Import Tokens' instead.",
        )
    except Exception as exc:
        return _error_redirect(request, f"Connection error: {exc}")

    if isinstance(result, tuple) and result[0] == "needs_mfa":
        # Store in-process MFA state
        mfa_key = str(uuid.uuid4())
        _MFA_SESSIONS[mfa_key] = (client, result[1])
        request.session["mfa_key"] = mfa_key
        return RedirectResponse("/auth/mfa", status_code=303)

    # No MFA — store tokens immediately
    request.session["token_b64"] = client.garth.dumps()
    request.session["flash_success"] = "Logged in successfully!"
    return RedirectResponse("/", status_code=303)


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

    request.session["token_b64"] = client.garth.dumps()
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

    request.session["token_b64"] = token
    request.session["flash_success"] = "Tokens imported successfully!"
    return RedirectResponse("/", status_code=303)


@app.get("/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


# ---------------------------------------------------------------------------
# Workout generation
# ---------------------------------------------------------------------------

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
        request.session.pop("token_b64", None)
        return _error_redirect(
            request,
            "Authentication failed. Your tokens may have expired. Please log in again."
        )
    except Exception as exc:
        logger.exception("Upload failed")
        return _error_redirect(request, f"Upload failed: {exc}")

    return RedirectResponse("/", status_code=303)
