# tests/test_nutrition_models.py
from __future__ import annotations

import json
from collections.abc import Generator
from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from web.db import Base
from web.models import NutritionPlan, Notification, User


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _make_user(db: Session) -> User:
    u = User(email="test@example.com")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def test_nutrition_plan_created(db: Session) -> None:
    user = _make_user(db)
    plan = NutritionPlan(
        user_id=user.id,
        week_start=date(2026, 4, 13),
        status="ready",
        plan_json=json.dumps({"days": [], "groceries": [], "reminders": []}),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    assert plan.id is not None
    assert plan.status == "ready"


def test_notification_created(db: Session) -> None:
    user = _make_user(db)
    plan = NutritionPlan(
        user_id=user.id,
        week_start=date(2026, 4, 13),
        status="ready",
        plan_json="{}",
    )
    db.add(plan)
    db.commit()
    notif = Notification(
        user_id=user.id,
        nutrition_plan_id=plan.id,
        scheduled_for=datetime(2026, 4, 18, 20, 0),
        channel="both",
        title_key="reminder_defrost_title",
        body="Defrost chicken tonight",
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    assert notif.id is not None
    assert notif.sent_at is None


def test_user_nutrition_profile(db: Session) -> None:
    user = _make_user(db)
    profile = {"meals_per_day": 3, "cooking_time": "medium", "avoid": ["liver"]}
    user.nutrition_profile_json = json.dumps(profile)
    db.commit()
    db.refresh(user)
    assert json.loads(user.nutrition_profile_json)["meals_per_day"] == 3


def test_recipe_cache_created(db: Session) -> None:
    from web.models import RecipeCache
    recipe_blob = json.dumps({"servings": 2, "prep_time_min": 5, "cook_time_min": 15, "steps": ["s1"], "tips": []})
    cache = RecipeCache(meal_id="breakfast_001", recipe_en=recipe_blob, recipe_he=recipe_blob)
    db.add(cache)
    db.commit()
    db.refresh(cache)
    assert cache.id is not None
    assert cache.meal_id == "breakfast_001"


def test_recipe_cache_meal_id_unique(db: Session) -> None:
    from sqlalchemy.exc import IntegrityError
    from web.models import RecipeCache
    blob = json.dumps({"servings": 1, "prep_time_min": 1, "cook_time_min": 1, "steps": [], "tips": []})
    db.add(RecipeCache(meal_id="dup_001", recipe_en=blob, recipe_he=blob))
    db.commit()
    db.add(RecipeCache(meal_id="dup_001", recipe_en=blob, recipe_he=blob))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
