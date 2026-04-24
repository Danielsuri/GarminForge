# tests/test_routes_suggest.py
"""Tests for POST /nutrition/suggest and POST /nutrition/suggest/confirm routes."""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from web.db import Base, get_db
from web.models import MealSuggestion, User

# Build a minimal valid meal JSON for use in tests
VALID_MEAL = {
    "id": "suggestion_test001",
    "type": "breakfast",
    "name_en": "Test oatmeal",
    "name_he": "שיבולת לבדיקה",
    "kcal": 350,
    "macros": {"protein_g": 10, "carbs_g": 60, "fat_g": 8},
    "cooking_time": "quick",
    "positive_tags": ["vegan"],
    "ingredient_flags": ["contains_gluten"],
    "ingredients": [{"item_en": "Oats", "item_he": "שיבולת", "qty": "80g", "category": "pantry"}],
    "prep_note_en": None,
    "prep_note_he": None,
}


@pytest.fixture()
def app_with_db():
    """Create a test app with an in-memory DB and a logged-in test user."""
    from web.app import app

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Create a user and inject into session so require_user can find them
    db = TestSession()
    user = User(email="test@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)

    client = TestClient(app, raise_server_exceptions=False)

    # Patch require_user to always return the test user
    with patch("web.routes_nutrition.require_user", return_value=user):
        yield client, db, user

    app.dependency_overrides.clear()
    db.close()


def test_suggest_returns_400_on_empty_description(app_with_db):
    client, db, user = app_with_db
    r = client.post("/nutrition/suggest", json={"description": "   "})
    assert r.status_code == 400


def test_suggest_returns_502_on_ai_failure(app_with_db):
    client, db, user = app_with_db
    with patch("web.routes_nutrition.get_ai_provider") as mock_ai:
        mock_ai.return_value.complete.side_effect = RuntimeError("AI down")
        r = client.post("/nutrition/suggest", json={"description": "Greek yogurt"})
    assert r.status_code == 502


def test_suggest_returns_enriched_meal(app_with_db):
    client, db, user = app_with_db
    with patch("web.routes_nutrition.get_ai_provider") as mock_ai:
        mock_ai.return_value.complete.return_value = json.dumps(VALID_MEAL)
        r = client.post("/nutrition/suggest", json={"description": "Test oatmeal"})
    assert r.status_code == 200
    data = r.json()
    assert data["name_en"] == "Test oatmeal"
    assert data["id"].startswith("suggestion_")


def test_confirm_saves_to_db(app_with_db):
    client, db, user = app_with_db
    r = client.post("/nutrition/suggest/confirm", json={"meal_json": VALID_MEAL})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "id" in body
    # Verify DB row was created
    suggestion = db.query(MealSuggestion).filter_by(user_id=user.id).first()
    assert suggestion is not None
    assert suggestion.status == "pending"
    meal = json.loads(suggestion.meal_json)
    assert meal["name_en"] == "Test oatmeal"
