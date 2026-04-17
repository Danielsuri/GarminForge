"""Tests for Strava data passed to the profile template."""

from __future__ import annotations
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

from web.strava_insights import RecoveryStatus
from web.routes_my import _build_strava_profile_ctx


def _user_with_strava(activities: list[dict] | None = None) -> MagicMock:
    from web.models import User

    user = MagicMock(spec=User)
    user.strava_token_json = (
        '{"access_token":"x","refresh_token":"y","expires_at":9999999999,"token_type":"Bearer"}'
    )
    user.strava_athlete_id = "12345"
    user.strava_synced_at = datetime(2026, 4, 16, 10, 0, tzinfo=timezone.utc)
    user.strava_activities_json = json.dumps(activities or [])
    return user


def _user_without_strava() -> MagicMock:
    from web.models import User

    user = MagicMock(spec=User)
    user.strava_token_json = None
    user.strava_athlete_id = None
    user.strava_synced_at = None
    user.strava_activities_json = None
    return user


def test_not_connected_ctx() -> None:
    """User without Strava → strava_connected False, no recovery."""
    ctx = _build_strava_profile_ctx(_user_without_strava())
    assert ctx["strava_connected"] is False
    assert ctx["strava_recovery"] is None


def test_connected_no_activities_ctx() -> None:
    """Connected but no activities → strava_connected True, no recovery."""
    ctx = _build_strava_profile_ctx(_user_with_strava(activities=[]))
    assert ctx["strava_connected"] is True
    assert ctx["strava_recovery"] is None


def test_connected_with_activities_ctx() -> None:
    """Connected with activities → strava_recovery is a RecoveryStatus."""
    ctx = _build_strava_profile_ctx(_user_with_strava(activities=[{"id": 1}]))
    assert ctx["strava_connected"] is True
    assert isinstance(ctx["strava_recovery"], RecoveryStatus)
