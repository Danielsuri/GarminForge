# tests/test_routes_recipe.py
"""Tests for GET /nutrition/meals/{meal_id}/recipe."""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from web.db import Base, get_db
from web.models import RecipeCache, User

VALID_RECIPE_RESPONSE = {
    "recipe_en": {
        "servings": 2,
        "prep_time_min": 10,
        "cook_time_min": 20,
        "steps": ["Step 1", "Step 2"],
        "tips": ["Tip 1"],
    },
    "recipe_he": {
        "servings": 2,
        "prep_time_min": 10,
        "cook_time_min": 20,
        "steps": ["שלב 1", "שלב 2"],
        "tips": ["טיפ 1"],
    },
}

POOL_MEAL = {
    "id": "breakfast_001",
    "type": "breakfast",
    "name_en": "Shakshuka",
    "name_he": "שקשוקה",
    "kcal": 420,
    "macros": {"protein_g": 22, "carbs_g": 18, "fat_g": 28},
    "cooking_time": "medium",
    "positive_tags": [],
    "ingredient_flags": [],
    "ingredients": [
        {"item_en": "Eggs", "item_he": "ביצים", "qty": "4", "category": "protein"},
    ],
    "prep_note_en": None,
    "prep_note_he": None,
}


@pytest.fixture()
def app_with_db():
    """Test app with in-memory DB and a patched logged-in user."""
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

    db = TestSession()
    user = User(email="test@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)

    client = TestClient(app, raise_server_exceptions=False)

    with patch("web.routes_nutrition.require_user", return_value=user):
        yield client, db, user

    app.dependency_overrides.clear()
    db.close()


def test_recipe_returns_cached_without_ai_call(app_with_db):
    client, db, user = app_with_db
    recipe_en = json.dumps(VALID_RECIPE_RESPONSE["recipe_en"])
    recipe_he = json.dumps(VALID_RECIPE_RESPONSE["recipe_he"])
    db.add(RecipeCache(meal_id="breakfast_001", recipe_en=recipe_en, recipe_he=recipe_he))
    db.commit()

    with patch("web.routes_nutrition.get_ai_provider") as mock_ai:
        r = client.get("/nutrition/meals/breakfast_001/recipe")

    assert r.status_code == 200
    mock_ai.assert_not_called()
    data = r.json()
    assert data["recipe_en"]["servings"] == 2
    assert data["recipe_he"]["steps"][0] == "שלב 1"


def test_recipe_generates_and_caches_on_cache_miss(app_with_db):
    client, db, user = app_with_db

    with patch("web.routes_nutrition.load_pool", return_value=[POOL_MEAL]):
        with patch("web.routes_nutrition.get_ai_provider") as mock_ai:
            mock_ai.return_value.complete.return_value = json.dumps(VALID_RECIPE_RESPONSE)
            r = client.get("/nutrition/meals/breakfast_001/recipe")

    assert r.status_code == 200
    data = r.json()
    assert data["recipe_en"]["steps"] == ["Step 1", "Step 2"]

    cached = db.query(RecipeCache).filter_by(meal_id="breakfast_001").first()
    assert cached is not None
    assert json.loads(cached.recipe_en)["cook_time_min"] == 20


def test_recipe_returns_502_on_ai_failure(app_with_db):
    client, db, user = app_with_db

    with patch("web.routes_nutrition.load_pool", return_value=[POOL_MEAL]):
        with patch("web.routes_nutrition.get_ai_provider") as mock_ai:
            mock_ai.return_value.complete.side_effect = RuntimeError("AI down")
            r = client.get("/nutrition/meals/breakfast_001/recipe")

    assert r.status_code == 502


def test_recipe_returns_404_for_unknown_meal(app_with_db):
    client, db, user = app_with_db

    with patch("web.routes_nutrition.load_pool", return_value=[]):
        r = client.get("/nutrition/meals/nonexistent_999/recipe")

    assert r.status_code == 404
