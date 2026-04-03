"""
GarminForge account authentication routes:
  POST /auth/register            — email + password signup
  GET  /auth/login-forge         — login page
  POST /auth/login-forge         — login submit
  GET  /auth/google              — redirect to Google OAuth
  GET  /auth/google/callback     — Google OAuth callback
  GET  /auth/apple               — redirect to Apple Sign-In
  POST /auth/apple/callback      — Apple Sign-In callback (form_post)

Environment variables:
  GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET   — Google OAuth credentials
  APPLE_CLIENT_ID                           — Apple Services ID (e.g. com.yourapp.web)
  APPLE_TEAM_ID                             — 10-char Apple Developer Team ID
  APPLE_KEY_ID                              — Key ID from Apple Developer portal
  APPLE_PRIVATE_KEY                         — Contents of .p8 file (newlines as \\n)
  APPLE_PRIVATE_KEY_PATH                    — Path to .p8 file (alternative to above)
  REDIRECT_BASE_URL                         — Override base URL for OAuth callbacks
                                              (e.g. https://garminforge.yourdomain.com)
                                              Required if running behind a reverse proxy.
"""
from __future__ import annotations

import base64
import hmac
import json
import logging
import os
import secrets
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import httpx
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from web.auth_utils import (
    get_current_user,
    hash_password,
    login_session,
    maybe_migrate_file_token,
    verify_password,
)
from web.db import get_db
from web.models import User
from web.rendering import render_template

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth")

# ---------------------------------------------------------------------------
# Module-level OAuth singleton.
# IMPORTANT: must be a single instance — authlib caches OIDC discovery docs
# and state on the OAuth object. Creating a new instance per-request breaks
# the authorize_redirect → authorize_access_token handshake.
# ---------------------------------------------------------------------------
_oauth = OAuth()
_google_registered = False


def _ensure_google_registered() -> bool:
    """Register Google with the singleton OAuth instance (idempotent)."""
    global _google_registered
    if _google_registered:
        return True
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        return False
    _oauth.register(
        name="google",
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    _google_registered = True
    return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _callback_url(request: Request, path: str) -> str:
    """Build an OAuth callback URL.

    Respects REDIRECT_BASE_URL env var — set this when the app is behind a
    reverse proxy / Cloudflare Tunnel so callbacks use the public HTTPS URL
    instead of the internal http://localhost address.
    """
    base = os.environ.get("REDIRECT_BASE_URL", "").rstrip("/")
    if not base:
        # str(request.base_url) already ends with "/"
        base = str(request.base_url).rstrip("/")
    return f"{base}{path}"


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def _social_flags() -> dict[str, bool]:
    """Return which social login providers are currently configured."""
    return {
        "google_enabled": bool(
            os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET")
        ),
        "apple_enabled": _apple_configured(),
    }


@router.get("/register")
async def register_page(request: Request, db: Session = Depends(get_db)):
    if get_current_user(request, db):
        return RedirectResponse("/", status_code=303)
    return render_template("register.html", request, db=db, **_social_flags())


@router.post("/register")
async def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(default=""),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()

    if not email or "@" not in email:
        return render_template(
            "register.html", request, db=db, flash_error="Please enter a valid email address."
        )
    if len(password) < 8:
        return render_template(
            "register.html", request, db=db, flash_error="Password must be at least 8 characters."
        )
    if db.query(User).filter_by(email=email).first():
        return render_template(
            "register.html",
            request,
            db=db,
            flash_error="An account with this email already exists.",
        )

    user = User(
        email=email,
        hashed_password=hash_password(password),
        display_name=display_name.strip() or None,
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    maybe_migrate_file_token(user, db)
    login_session(request, user, db)
    request.session["flash_success"] = "Account created! Connect your Garmin account below."
    return RedirectResponse("/", status_code=303)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


@router.get("/login-forge")
async def login_forge_page(request: Request, db: Session = Depends(get_db)):
    if get_current_user(request, db):
        return RedirectResponse("/", status_code=303)
    return render_template("login_forge.html", request, db=db, **_social_flags())


@router.post("/login-forge")
async def login_forge_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    user = db.query(User).filter_by(email=email).first()

    if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
        return render_template(
            "login_forge.html", request, db=db, flash_error="Invalid email or password."
        )

    maybe_migrate_file_token(user, db)
    login_session(request, user, db)
    return RedirectResponse("/", status_code=303)


# ---------------------------------------------------------------------------
# Google OAuth (OIDC)
# ---------------------------------------------------------------------------


@router.get("/google")
async def google_redirect(request: Request):
    if not _ensure_google_registered():
        request.session["flash_error"] = "Google sign-in is not configured on this server."
        return RedirectResponse("/auth/login-forge", status_code=303)
    redirect_uri = _callback_url(request, "/auth/google/callback")
    return await _oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    if not _ensure_google_registered():
        return RedirectResponse("/auth/login-forge", status_code=303)

    try:
        token = await _oauth.google.authorize_access_token(request)
    except Exception as exc:
        logger.exception("Google OAuth token exchange failed")
        request.session["flash_error"] = f"Google sign-in failed: {exc}"
        return RedirectResponse("/auth/login-forge", status_code=303)

    info = token.get("userinfo") or {}
    sub: str = info.get("sub", "")
    email: str = info.get("email", "").strip().lower()
    name: str = info.get("name", "")

    if not email or not sub:
        request.session["flash_error"] = "Google did not return an email address."
        return RedirectResponse("/auth/login-forge", status_code=303)

    user = db.query(User).filter_by(google_sub=sub).first()
    if user is None:
        user = db.query(User).filter_by(email=email).first()
        if user:
            user.google_sub = sub
            user.is_verified = True
            db.commit()
        else:
            user = User(
                email=email,
                google_sub=sub,
                display_name=name or None,
                is_verified=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

    maybe_migrate_file_token(user, db)
    login_session(request, user, db)
    return RedirectResponse("/", status_code=303)


# ---------------------------------------------------------------------------
# Apple Sign-In
# ---------------------------------------------------------------------------


def _apple_configured() -> bool:
    return all(
        os.environ.get(k)
        for k in ["APPLE_CLIENT_ID", "APPLE_TEAM_ID", "APPLE_KEY_ID"]
    ) and bool(
        os.environ.get("APPLE_PRIVATE_KEY") or os.environ.get("APPLE_PRIVATE_KEY_PATH")
    )


def _apple_private_key() -> str:
    key = os.environ.get("APPLE_PRIVATE_KEY", "")
    if key:
        return key.replace("\\n", "\n")
    path = os.environ.get("APPLE_PRIVATE_KEY_PATH", "")
    if path:
        return Path(path).read_text(encoding="utf-8")
    raise ValueError("APPLE_PRIVATE_KEY or APPLE_PRIVATE_KEY_PATH must be set")


def _apple_client_secret() -> str:
    """Generate a short-lived JWT used as Apple's client_secret."""
    from authlib.jose import jwt as jose_jwt

    now = int(datetime.now(timezone.utc).timestamp())
    header = {"alg": "ES256", "kid": os.environ["APPLE_KEY_ID"]}
    claims = {
        "iss": os.environ["APPLE_TEAM_ID"],
        "iat": now,
        "exp": now + 15_777_000,  # 6 months (Apple's max)
        "aud": "https://appleid.apple.com",
        "sub": os.environ["APPLE_CLIENT_ID"],
    }
    token = jose_jwt.encode(header, claims, _apple_private_key())
    return token.decode() if isinstance(token, bytes) else str(token)


def _decode_apple_id_token(id_token: str) -> dict[str, str]:
    """Decode Apple id_token payload (claims only, without signature verification).

    The token exchange itself authenticates the code; full JWK verification
    can be added if needed for production hardening.
    """
    parts = id_token.split(".")
    if len(parts) < 2:
        return {}
    payload = parts[1] + "=" * (4 - len(parts[1]) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return {}


@router.get("/apple")
async def apple_redirect(request: Request):
    if not _apple_configured():
        request.session["flash_error"] = "Apple sign-in is not configured on this server."
        return RedirectResponse("/auth/login-forge", status_code=303)

    state = secrets.token_urlsafe(16)
    request.session["apple_state"] = state

    params = urllib.parse.urlencode({
        "client_id": os.environ["APPLE_CLIENT_ID"],
        "redirect_uri": _callback_url(request, "/auth/apple/callback"),
        "response_type": "code",
        "scope": "name email",
        "response_mode": "form_post",
        "state": state,
    })
    return RedirectResponse(
        f"https://appleid.apple.com/auth/authorize?{params}", status_code=302
    )


@router.post("/apple/callback")
async def apple_callback(request: Request, db: Session = Depends(get_db)):
    """Apple POSTs form data here (response_mode=form_post)."""
    form = await request.form()
    code: str = form.get("code", "")  # type: ignore[assignment]
    state: str = form.get("state", "")  # type: ignore[assignment]
    id_token_str: str = form.get("id_token", "")  # type: ignore[assignment]
    user_json: str = form.get("user", "")  # type: ignore[assignment]  # first login only

    # Verify CSRF state
    expected = request.session.pop("apple_state", "")
    if not state or not expected or not hmac.compare_digest(state, expected):
        request.session["flash_error"] = "Apple sign-in failed: state mismatch."
        return RedirectResponse("/auth/login-forge", status_code=303)

    if not code:
        error = form.get("error", "unknown error")
        request.session["flash_error"] = f"Apple sign-in failed: {error}"
        return RedirectResponse("/auth/login-forge", status_code=303)

    # Exchange auth code for tokens to get a verified id_token
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://appleid.apple.com/auth/token",
                data={
                    "client_id": os.environ["APPLE_CLIENT_ID"],
                    "client_secret": _apple_client_secret(),
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": _callback_url(request, "/auth/apple/callback"),
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0,
            )
        token_data = resp.json()
        if "error" in token_data:
            raise ValueError(token_data["error"])
        id_token_str = token_data.get("id_token", id_token_str)
    except Exception as exc:
        logger.exception("Apple token exchange failed")
        request.session["flash_error"] = f"Apple sign-in failed: {exc}"
        return RedirectResponse("/auth/login-forge", status_code=303)

    if not id_token_str:
        request.session["flash_error"] = "Apple sign-in failed: no identity token received."
        return RedirectResponse("/auth/login-forge", status_code=303)

    claims = _decode_apple_id_token(id_token_str)
    sub: str = claims.get("sub", "")
    email: str = claims.get("email", "").strip().lower()

    # Name is only sent on the very first authorization
    display_name: str | None = None
    if user_json:
        try:
            ui = json.loads(user_json)
            parts = [
                ui.get("name", {}).get("firstName", ""),
                ui.get("name", {}).get("lastName", ""),
            ]
            display_name = " ".join(p for p in parts if p) or None
        except Exception:
            pass

    if not sub:
        request.session["flash_error"] = "Apple sign-in failed: no user identifier."
        return RedirectResponse("/auth/login-forge", status_code=303)

    # Upsert: look up by apple_sub, then by email (to merge with existing account)
    user = db.query(User).filter_by(apple_sub=sub).first()
    if user is None:
        if email:
            user = db.query(User).filter_by(email=email).first()
        if user:
            user.apple_sub = sub
            user.is_verified = True
            if display_name and not user.display_name:
                user.display_name = display_name
            db.commit()
        else:
            # Apple private relay emails look like xyz@privaterelay.appleid.com
            user = User(
                email=email or f"apple_{sub[:8]}@privaterelay.appleid.com",
                apple_sub=sub,
                display_name=display_name,
                is_verified=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    else:
        # Update name if we have it now (only sent on first auth per Apple's policy)
        if display_name and not user.display_name:
            user.display_name = display_name
            db.commit()

    maybe_migrate_file_token(user, db)
    login_session(request, user, db)
    return RedirectResponse("/", status_code=303)
