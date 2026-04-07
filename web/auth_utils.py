"""
GarminForge account auth helpers: password hashing, session management, token migration.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import bcrypt
from fastapi import Request
from sqlalchemy.orm import Session

from web.models import User

logger = logging.getLogger(__name__)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def get_current_user(request: Request, db: Session) -> User | None:
    """Return the logged-in GarminForge User or None."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.get(User, user_id)


def require_user(request: Request, db: Session) -> User | None:
    """Return the current user or None (caller should redirect to login when None)."""
    return get_current_user(request, db)


def login_session(request: Request, user: User, db: Session) -> None:
    """Write user_id into the session and update last_login_at."""
    request.session["user_id"] = user.id
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()


def logout_session(request: Request) -> None:
    """Clear GarminForge session keys."""
    request.session.pop("user_id", None)


def maybe_migrate_file_token(user: User, db: Session) -> None:
    """One-time migration: copy ~/.garminforge_token to User.garmin_token_b64."""
    if user.garmin_token_b64:
        return
    saved = Path.home() / ".garminforge_token"
    if not saved.exists():
        return
    try:
        token_b64 = saved.read_text(encoding="utf-8").strip()
        if token_b64:
            user.garmin_token_b64 = token_b64
            db.commit()
            logger.info("Migrated Garmin token from file to DB for user %s", user.id)
    except Exception as exc:
        logger.warning("Token migration failed: %s", exc)
