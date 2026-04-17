"""Strava OAuth2 connect/disconnect and activity sync routes.

Routes
------
GET  /strava/connect      Redirect to Strava authorization page
GET  /strava/callback     Handle OAuth2 callback, store tokens, initial sync
POST /strava/sync         Manual "Sync Now" — fetch activities, update cache
POST /strava/disconnect   Remove Strava connection from user account
"""

from __future__ import annotations

import json
import logging
import os
import secrets
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from web.auth_utils import get_current_user
from web.db import get_db
from web.models import ProgramSession, User
from web.strava_client import StravaToken, strava_client_from_user
from web.strava_insights import (
    calibrate_fitness_rank,
    compact_activity,
    recovery_score,
    reschedule_if_needed,
)
from garminforge.exceptions import StravaAuthError, StravaRateLimitError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/strava", tags=["strava"])

_AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
_TOKEN_URL = "https://www.strava.com/oauth/token"
_SCOPES = "activity:read_all,activity:write"


def _client_id() -> str:
    val = os.environ.get("STRAVA_CLIENT_ID", "")
    if not val:
        raise RuntimeError("STRAVA_CLIENT_ID environment variable not set")
    return val


def _client_secret() -> str:
    val = os.environ.get("STRAVA_CLIENT_SECRET", "")
    if not val:
        raise RuntimeError("STRAVA_CLIENT_SECRET environment variable not set")
    return val


def _callback_url(request: Request) -> str:
    return str(request.url_for("strava_callback"))


def do_sync(user: User, db: Session) -> None:
    """Fetch latest Strava activities, update User cache, recalibrate fitness_rank,
    and reschedule any ProgramSessions that fall inside the recovery window.

    Public — also called by APScheduler in app.py.
    """
    client = strava_client_from_user(user, _client_id(), _client_secret())
    raw = client.list_activities(days_back=90)
    compact = [compact_activity(a) for a in raw]

    user.strava_activities_json = json.dumps(compact)
    user.strava_synced_at = datetime.now(timezone.utc)
    user.fitness_rank = calibrate_fitness_rank(compact, user.fitness_rank)

    # Persist refreshed token if it changed
    user.strava_token_json = json.dumps(client.token.as_dict())
    db.commit()

    # Refresh future program sessions to match updated fitness_rank
    from web.program_generator import refresh_future_program_sessions
    refreshed = refresh_future_program_sessions(user, db)
    if refreshed:
        logger.info("Strava sync refreshed %d future sessions for user %s", refreshed, user.id)

    # Reschedule upcoming program sessions if user is fatigued
    recovery = recovery_score(compact)
    upcoming = (
        db.query(ProgramSession)
        .filter(
            ProgramSession.program.has(user_id=user.id),
            ProgramSession.completed_at.is_(None),
            ProgramSession.scheduled_date.isnot(None),
        )
        .all()
    )
    reschedule_if_needed(upcoming, recovery, db)


@router.get("/connect")
async def strava_connect(request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    """Redirect to Strava to begin OAuth2 authorization."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse("/auth/login-forge", status_code=303)

    state = secrets.token_urlsafe(24)
    request.session["strava_oauth_state"] = state

    callback = _callback_url(request)
    url = (
        f"{_AUTHORIZE_URL}"
        f"?client_id={_client_id()}"
        f"&redirect_uri={callback}"
        f"&response_type=code"
        f"&scope={_SCOPES}"
        f"&approval_prompt=auto"
        f"&state={state}"
    )
    return RedirectResponse(url, status_code=303)


@router.get("/callback", name="strava_callback")
async def strava_callback(
    request: Request,
    code: str = "",
    error: str = "",
    state: str = "",
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Exchange authorization code for tokens, store them, run initial sync."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse("/auth/login-forge", status_code=303)

    # Verify CSRF state token
    expected_state = request.session.pop("strava_oauth_state", None)
    if not expected_state or not secrets.compare_digest(expected_state, state):
        logger.warning("Strava OAuth state mismatch — possible CSRF")
        request.session["flash"] = "Strava connection failed: invalid state."
        return RedirectResponse("/my/profile", status_code=303)

    if error:
        logger.warning("Strava OAuth error: %s", error)
        request.session["flash"] = f"Strava connection failed: {error}"
        return RedirectResponse("/my/profile", status_code=303)

    if not code:
        request.session["flash"] = "No authorization code received from Strava."
        return RedirectResponse("/my/profile", status_code=303)

    try:
        resp = httpx.post(
            _TOKEN_URL,
            data={
                "client_id": _client_id(),
                "client_secret": _client_secret(),
                "code": code,
                "grant_type": "authorization_code",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.exception("Strava token exchange failed")
        request.session["flash"] = f"Strava connection error: {exc}"
        return RedirectResponse("/my/profile", status_code=303)

    token = StravaToken.from_dict(data)
    athlete = data.get("athlete", {})
    user.strava_token_json = json.dumps(token.as_dict())
    user.strava_athlete_id = str(athlete.get("id", ""))
    db.commit()

    try:
        do_sync(user, db)
    except (StravaAuthError, StravaRateLimitError) as exc:
        logger.warning("Initial Strava sync failed: %s", exc)

    request.session["flash"] = "Strava connected successfully!"
    return RedirectResponse("/my/profile", status_code=303)


@router.post("/sync")
async def strava_sync(request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    """Manual sync: fetch latest activities, update cache, recalibrate rank."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse("/auth/login-forge", status_code=303)

    if not user.strava_token_json:
        request.session["flash"] = "No Strava account connected."
        return RedirectResponse("/my/profile", status_code=303)

    try:
        do_sync(user, db)
        request.session["flash"] = "Strava synced successfully."
    except StravaAuthError:
        request.session["flash"] = "Strava session expired — please reconnect."
    except StravaRateLimitError:
        request.session["flash"] = "Strava rate limit reached — try again in 15 min."
    except Exception as exc:
        logger.exception("Strava sync error")
        request.session["flash"] = f"Sync error: {exc}"

    return RedirectResponse("/my/profile", status_code=303)


@router.post("/disconnect")
async def strava_disconnect(request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    """Remove Strava connection and clear all cached data."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse("/auth/login-forge", status_code=303)

    user.strava_athlete_id = None
    user.strava_token_json = None
    user.strava_activities_json = None
    user.strava_synced_at = None
    db.commit()

    request.session["flash"] = "Strava disconnected."
    return RedirectResponse("/my/profile", status_code=303)
