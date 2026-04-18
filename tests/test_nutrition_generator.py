# tests/test_nutrition_generator.py
from __future__ import annotations

import json
from collections.abc import Generator
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from web.db import Base
from web.models import Notification, NutritionPlan, User
from web.nutrition_generator import (
    PLAN_SCHEMA_EXAMPLE,
    generate_weekly_plan,
    get_todays_meals,
    get_todays_reminder,
    last_sunday,
)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _make_user(db: Session) -> User:
    u = User(
        email="test@example.com",
        nutrition_profile_json=json.dumps({
            "meals_per_day": 3, "cooking_time": "medium", "calorie_mode": "macros",
            "allergies": [], "avoid": ["liver"], "cant_resist": ["avocado"],
        }),
        diet_json=json.dumps(["keto"]),
        fitness_goals_json=json.dumps(["build_muscle"]),
        preferred_lang="en",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


VALID_PLAN = json.dumps({
    "days": [{"date": "2026-04-12", "meals": [
        {"type": "breakfast", "name": "Avocado eggs", "kcal": 420,
         "macros": {"protein_g": 22, "carbs_g": 6, "fat_g": 20}},
    ]}],
    "groceries": [{"item": "Avocado", "qty": "4 pcs", "category": "vegetables"}],
    "reminders": [{"day": "2026-04-18", "text": "Defrost chicken tonight"}],
})


def test_last_sunday() -> None:
    assert last_sunday(date(2026, 4, 18)) == date(2026, 4, 12)  # Saturday → previous Sunday
    assert last_sunday(date(2026, 4, 12)) == date(2026, 4, 12)  # Sunday itself


def test_generate_creates_plan(db: Session) -> None:
    user = _make_user(db)
    mock_provider = MagicMock()
    mock_provider.complete.return_value = VALID_PLAN
    with patch("web.nutrition_generator.get_ai_provider", return_value=mock_provider):
        with patch("web.nutrition_generator.date") as md:
            md.today.return_value = date(2026, 4, 18)
            md.fromisoformat = date.fromisoformat
            md.fromordinal = date.fromordinal
            plan = generate_weekly_plan(user, db)
    assert plan.status == "ready"
    assert plan.week_start == date(2026, 4, 12)
    assert mock_provider.complete.called


def test_generate_returns_cached(db: Session) -> None:
    user = _make_user(db)
    existing = NutritionPlan(
        user_id=user.id, week_start=date(2026, 4, 12), status="ready", plan_json=VALID_PLAN
    )
    db.add(existing)
    db.commit()
    mock_provider = MagicMock()
    with patch("web.nutrition_generator.get_ai_provider", return_value=mock_provider):
        with patch("web.nutrition_generator.date") as md:
            md.today.return_value = date(2026, 4, 18)
            md.fromisoformat = date.fromisoformat
            md.fromordinal = date.fromordinal
            plan = generate_weekly_plan(user, db)
    assert not mock_provider.complete.called
    assert plan.id == existing.id


def test_get_todays_meals(db: Session) -> None:
    user = _make_user(db)
    plan = NutritionPlan(
        user_id=user.id, week_start=date(2026, 4, 12), status="ready", plan_json=VALID_PLAN
    )
    db.add(plan)
    db.commit()
    meals = get_todays_meals(plan, today=date(2026, 4, 12))
    assert len(meals) == 1
    assert meals[0]["name"] == "Avocado eggs"


def test_reminders_create_notifications(db: Session) -> None:
    user = _make_user(db)
    mock_provider = MagicMock()
    mock_provider.complete.return_value = VALID_PLAN
    with patch("web.nutrition_generator.get_ai_provider", return_value=mock_provider):
        with patch("web.nutrition_generator.date") as md:
            md.today.return_value = date(2026, 4, 18)
            md.fromisoformat = date.fromisoformat
            md.fromordinal = date.fromordinal
            generate_weekly_plan(user, db)
    notifs = db.query(Notification).filter_by(user_id=user.id).all()
    assert len(notifs) == 1
    assert "Defrost" in notifs[0].body


def test_get_todays_reminder(db: Session) -> None:
    user = _make_user(db)
    plan = NutritionPlan(
        user_id=user.id, week_start=date(2026, 4, 12), status="ready", plan_json=VALID_PLAN
    )
    db.add(plan)
    db.commit()
    reminder = get_todays_reminder(plan, today=date(2026, 4, 18))
    assert reminder == "Defrost chicken tonight"
    assert get_todays_reminder(plan, today=date(2026, 4, 13)) is None
