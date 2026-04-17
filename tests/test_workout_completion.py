"""Tests for the workout completion flow (POST /workout/complete/{session_id})."""

from __future__ import annotations
import json
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from web.app import app
from web.models import ProgramSession, User


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def _make_session(completed_at: datetime | None = None) -> ProgramSession:
    s = MagicMock(spec=ProgramSession)
    s.id = "sess-1"
    s.program_id = "prog-1"
    s.focus = "Upper Body"
    s.week_num = 1
    s.day_num = 1
    s.garmin_payload_json = json.dumps({"estimatedDurationInSecs": 2700})
    s.exercises_json = json.dumps([])
    s.completed_at = completed_at
    s.actual_duration_minutes = None
    s.strava_activity_id = None
    s.scheduled_date = None
    return s


def test_complete_get_unauthenticated(client: TestClient) -> None:
    """GET /my/sessions/{id}/complete redirects when not logged in."""
    resp = client.get("/my/sessions/sess-1/complete", follow_redirects=False)
    assert resp.status_code in (302, 303)


def test_complete_post_marks_completed() -> None:
    """POST /workout/complete marks session.completed_at and actual_duration_minutes."""
    session_obj = _make_session()
    user = MagicMock(spec=User)
    user.id = "user-1"
    user.strava_token_json = None
    user.strava_activities_json = None

    db = MagicMock()
    db.query.return_value.filter_by.return_value.first.return_value = session_obj

    # Call the helper directly
    from web.routes_programs import _mark_complete

    _mark_complete(session_obj, actual_duration=45, post_to_strava=False, user=user, db=db)

    assert session_obj.completed_at is not None
    assert session_obj.actual_duration_minutes == 45
    db.commit.assert_called_once()
