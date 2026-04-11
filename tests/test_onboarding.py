"""Tests for onboarding questionnaire fields."""
import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from web.app import app
from web.models import User, Program, ProgramSession

client = TestClient(app, raise_server_exceptions=False)


def test_onboarding_get_accessible_without_login():
    resp = client.get("/onboarding", follow_redirects=False)
    assert resp.status_code == 200


def test_root_redirects_unauthenticated_to_onboarding():
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert resp.headers["location"] in ("/onboarding", "http://testserver/onboarding")


def test_user_has_new_fields():
    u = User(email="t@test.com")
    assert hasattr(u, "age_range")
    assert hasattr(u, "preferred_days_json")
    assert hasattr(u, "height_cm")
    assert hasattr(u, "weight_kg")


def _make_user(**kwargs):
    defaults = dict(
        id="test-user-1",
        email="t@test.com",
        fitness_goals_json=json.dumps(["build_muscle"]),
        preferred_equipment_json=json.dumps(["barbell", "dumbbell"]),
        preferred_days_json=json.dumps(["Mon", "Wed", "Fri"]),
        fitness_level="Intermediate",
        questionnaire_completed=True,
    )
    defaults.update(kwargs)
    u = User(**{k: v for k, v in defaults.items()})
    return u


def test_root_authenticated_no_questionnaire_redirects_to_onboarding(monkeypatch):
    """Authenticated user with questionnaire_completed=False → /onboarding."""
    from unittest.mock import MagicMock
    import web.app as app_module

    fake_user = MagicMock()
    fake_user.questionnaire_completed = False

    orig_get_current_user = app_module.get_current_user
    monkeypatch.setattr(app_module, "get_current_user", lambda req, db: fake_user)

    try:
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code in (302, 303)
        assert "/onboarding" in resp.headers["location"]
    finally:
        monkeypatch.setattr(app_module, "get_current_user", orig_get_current_user)


def test_auto_generate_program_creates_program_and_sessions():
    from web.program_generator import auto_generate_program

    user = _make_user()
    db = MagicMock()
    db.query.return_value.filter_by.return_value.first.return_value = None
    added = []
    db.add.side_effect = added.append
    db.flush.return_value = None
    db.commit.return_value = None
    db.refresh.return_value = None

    program = auto_generate_program(user, db)

    assert isinstance(program, Program)
    assert program.goal == "build_muscle"
    assert program.periodization_type == "block"
    assert program.status == "active"
    # 3 days/week × 8 weeks = 24 sessions
    session_objects = [x for x in added if isinstance(x, ProgramSession)]
    assert len(session_objects) == 24


def test_auto_generate_program_maps_periodization():
    from web.program_generator import auto_generate_program

    for goal, expected_periodization in [
        ("burn_fat", "linear"),
        ("lose_weight", "linear"),
        ("build_muscle", "block"),
        ("build_strength", "block"),
        ("general_fitness", "undulating"),
        ("endurance", "undulating"),
    ]:
        user = _make_user(fitness_goals_json=json.dumps([goal]))
        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.return_value = None
        db.add.side_effect = lambda x: None
        db.flush.return_value = None
        db.commit.return_value = None
        db.refresh.return_value = None
        program = auto_generate_program(user, db)
        assert program.periodization_type == expected_periodization, f"goal={goal}"
