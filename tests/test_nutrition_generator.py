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

# Small pool fixture used in all generator tests
POOL_FIXTURE = [
    {
        "id": "breakfast_001",
        "type": "breakfast",
        "name_en": "Shakshuka",
        "name_he": "שקשוקה",
        "kcal": 420,
        "macros": {"protein_g": 22, "carbs_g": 18, "fat_g": 28},
        "cooking_time": "medium",
        "positive_tags": ["kosher", "vegetarian"],
        "ingredient_flags": ["contains_eggs"],
        "ingredients": [
            {"item_en": "Eggs", "item_he": "ביצים", "qty": "4", "category": "protein"},
        ],
        "prep_note_en": None,
        "prep_note_he": None,
    },
    {
        "id": "lunch_001",
        "type": "lunch",
        "name_en": "Chicken salad",
        "name_he": "סלט עוף",
        "kcal": 480,
        "macros": {"protein_g": 38, "carbs_g": 12, "fat_g": 22},
        "cooking_time": "quick",
        "positive_tags": ["kosher", "gluten-free", "dairy-free"],
        "ingredient_flags": ["contains_meat"],
        "ingredients": [
            {"item_en": "Chicken", "item_he": "עוף", "qty": "150g", "category": "protein"},
        ],
        "prep_note_en": None,
        "prep_note_he": None,
    },
    {
        "id": "dinner_001",
        "type": "dinner",
        "name_en": "Grilled salmon",
        "name_he": "סלמון על האש",
        "kcal": 550,
        "macros": {"protein_g": 42, "carbs_g": 5, "fat_g": 28},
        "cooking_time": "medium",
        "positive_tags": ["kosher", "gluten-free", "dairy-free"],
        "ingredient_flags": ["contains_fish"],
        "ingredients": [
            {"item_en": "Salmon", "item_he": "סלמון", "qty": "200g", "category": "protein"},
        ],
        "prep_note_en": "Defrost salmon the night before.",
        "prep_note_he": "הפשר סלמון לילה לפני.",
    },
]

# Claude selection response (IDs only)
SELECTION_RESPONSE = json.dumps({
    "days": [
        {"date": "2026-04-12", "meals": [
            {"type": "breakfast", "meal_id": "breakfast_001"},
            {"type": "lunch", "meal_id": "lunch_001"},
            {"type": "dinner", "meal_id": "dinner_001"},
        ]},
    ]
})


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
            "allergies": [], "avoid": [], "cant_resist": [],
        }),
        diet_json=json.dumps(["keto"]),
        fitness_goals_json=json.dumps(["build_muscle"]),
        preferred_lang="en",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def test_last_sunday() -> None:
    assert last_sunday(date(2026, 4, 18)) == date(2026, 4, 12)  # Saturday → prior Sunday
    assert last_sunday(date(2026, 4, 12)) == date(2026, 4, 12)  # Sunday itself


def test_generate_creates_plan(db: Session) -> None:
    user = _make_user(db)
    mock_provider = MagicMock()
    mock_provider.complete.return_value = SELECTION_RESPONSE
    with patch("web.nutrition_generator.get_ai_provider", return_value=mock_provider):
        with patch("web.nutrition_generator.load_pool", return_value=POOL_FIXTURE):
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
        user_id=user.id, week_start=date(2026, 4, 12), status="ready",
        plan_json=json.dumps({"days": [], "groceries": [], "reminders": []}),
    )
    db.add(existing)
    db.commit()
    mock_provider = MagicMock()
    with patch("web.nutrition_generator.get_ai_provider", return_value=mock_provider):
        with patch("web.nutrition_generator.load_pool", return_value=POOL_FIXTURE):
            with patch("web.nutrition_generator.date") as md:
                md.today.return_value = date(2026, 4, 18)
                md.fromisoformat = date.fromisoformat
                md.fromordinal = date.fromordinal
                plan = generate_weekly_plan(user, db)
    assert not mock_provider.complete.called
    assert plan.id == existing.id


def test_generate_resolves_meal_names(db: Session) -> None:
    user = _make_user(db)
    mock_provider = MagicMock()
    mock_provider.complete.return_value = SELECTION_RESPONSE
    with patch("web.nutrition_generator.get_ai_provider", return_value=mock_provider):
        with patch("web.nutrition_generator.load_pool", return_value=POOL_FIXTURE):
            with patch("web.nutrition_generator.date") as md:
                md.today.return_value = date(2026, 4, 18)
                md.fromisoformat = date.fromisoformat
                md.fromordinal = date.fromordinal
                plan = generate_weekly_plan(user, db)
    data = json.loads(plan.plan_json)
    meals = data["days"][0]["meals"]
    names = [m["name"] for m in meals]
    assert "Shakshuka" in names
    assert "Chicken salad" in names


def test_generate_creates_reminder_notification(db: Session) -> None:
    user = _make_user(db)
    mock_provider = MagicMock()
    mock_provider.complete.return_value = SELECTION_RESPONSE
    with patch("web.nutrition_generator.get_ai_provider", return_value=mock_provider):
        with patch("web.nutrition_generator.load_pool", return_value=POOL_FIXTURE):
            with patch("web.nutrition_generator.date") as md:
                md.today.return_value = date(2026, 4, 18)
                md.fromisoformat = date.fromisoformat
                md.fromordinal = date.fromordinal
                generate_weekly_plan(user, db)
    notifs = db.query(Notification).filter_by(user_id=user.id).all()
    # dinner_001 has prep_note, so one reminder should be created
    assert len(notifs) >= 1
    assert "Defrost" in notifs[0].body


def test_get_todays_meals(db: Session) -> None:
    user = _make_user(db)
    plan_data = {
        "days": [{"date": "2026-04-12", "meals": [
            {"type": "breakfast", "name": "Shakshuka", "kcal": 420, "macros": {"protein_g": 22, "carbs_g": 18, "fat_g": 28}}
        ]}],
        "groceries": [],
        "reminders": [],
    }
    plan = NutritionPlan(
        user_id=user.id, week_start=date(2026, 4, 12), status="ready",
        plan_json=json.dumps(plan_data),
    )
    db.add(plan)
    db.commit()
    meals = get_todays_meals(plan, today=date(2026, 4, 12))
    assert len(meals) == 1
    assert meals[0]["name"] == "Shakshuka"


def test_get_todays_reminder(db: Session) -> None:
    user = _make_user(db)
    plan_data = {
        "days": [],
        "groceries": [],
        "reminders": [{"day": "2026-04-11", "text": "Defrost salmon"}],
    }
    plan = NutritionPlan(
        user_id=user.id, week_start=date(2026, 4, 12), status="ready",
        plan_json=json.dumps(plan_data),
    )
    db.add(plan)
    db.commit()
    assert get_todays_reminder(plan, today=date(2026, 4, 11)) == "Defrost salmon"
    assert get_todays_reminder(plan, today=date(2026, 4, 12)) is None


def test_generate_includes_pending_suggestion(db: Session) -> None:
    from web.models import MealSuggestion

    user = _make_user(db)

    # A custom meal not in the static pool
    custom_meal = {
        "id": "suggestion_abc12345",
        "type": "breakfast",
        "name_en": "Custom oatmeal",
        "name_he": "שיבולת מותאמת",
        "kcal": 350,
        "macros": {"protein_g": 10, "carbs_g": 60, "fat_g": 8},
        "cooking_time": "quick",
        "positive_tags": ["vegan", "kosher"],
        "ingredient_flags": ["contains_gluten"],
        "ingredients": [
            {"item_en": "Oats", "item_he": "שיבולת", "qty": "80g", "category": "pantry"}
        ],
        "prep_note_en": None,
        "prep_note_he": None,
    }
    db.add(MealSuggestion(user_id=user.id, meal_json=json.dumps(custom_meal)))
    db.commit()

    # Selection response picks the custom meal
    selection = json.dumps({
        "days": [{"date": "2026-04-12", "meals": [
            {"type": "breakfast", "meal_id": "suggestion_abc12345"},
        ]}]
    })

    mock_provider = MagicMock()
    mock_provider.complete.return_value = selection
    with patch("web.nutrition_generator.get_ai_provider", return_value=mock_provider):
        with patch("web.nutrition_generator.load_pool", return_value=POOL_FIXTURE):
            with patch("web.nutrition_generator.date") as md:
                md.today.return_value = date(2026, 4, 18)
                md.fromisoformat = date.fromisoformat
                md.fromordinal = date.fromordinal
                plan = generate_weekly_plan(user, db)

    data = json.loads(plan.plan_json)
    names = [m["name"] for m in data["days"][0]["meals"]]
    assert "Custom oatmeal" in names


def test_build_plan_json_includes_meal_id() -> None:
    from web.nutrition_generator import _build_plan_json

    resolved = {
        "days": [
            {
                "date": "2026-04-27",
                "meals": [
                    {
                        "id": "breakfast_001",
                        "type": "breakfast",
                        "name_en": "Oatmeal",
                        "name_he": "שיבולת",
                        "kcal": 300,
                        "macros": {"protein_g": 10, "carbs_g": 50, "fat_g": 5},
                        "ingredients": [],
                    }
                ],
            }
        ]
    }
    result = _build_plan_json(resolved, lang="en")
    meal = result["days"][0]["meals"][0]
    assert meal["id"] == "breakfast_001"
