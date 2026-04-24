# tests/test_meal_selector.py
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from datetime import date

import pytest

# We'll monkeypatch the pool path to use a small test fixture
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
        "ingredient_flags": ["contains_eggs", "contains_dairy"],
        "ingredients": [
            {"item_en": "Eggs", "item_he": "ביצים", "qty": "4", "category": "protein"},
            {"item_en": "Feta cheese", "item_he": "גבינה פטה", "qty": "80g", "category": "dairy_fats"},
        ],
        "prep_note_en": None,
        "prep_note_he": None,
    },
    {
        "id": "lunch_001",
        "type": "lunch",
        "name_en": "Pork sandwich",
        "name_he": "כריך חזיר",
        "kcal": 500,
        "macros": {"protein_g": 30, "carbs_g": 40, "fat_g": 18},
        "cooking_time": "quick",
        "positive_tags": [],
        "ingredient_flags": ["contains_pork", "contains_gluten"],
        "ingredients": [
            {"item_en": "Pork", "item_he": "חזיר", "qty": "150g", "category": "protein"},
            {"item_en": "Bread", "item_he": "לחם", "qty": "2 slices", "category": "pantry"},
        ],
        "prep_note_en": None,
        "prep_note_he": None,
    },
    {
        "id": "dinner_001",
        "type": "dinner",
        "name_en": "Grilled chicken",
        "name_he": "עוף על האש",
        "kcal": 550,
        "macros": {"protein_g": 45, "carbs_g": 10, "fat_g": 22},
        "cooking_time": "elaborate",
        "positive_tags": ["kosher", "gluten-free", "dairy-free"],
        "ingredient_flags": ["contains_meat"],
        "ingredients": [
            {"item_en": "Chicken breast", "item_he": "חזה עוף", "qty": "200g", "category": "protein"},
            {"item_en": "Olive oil", "item_he": "שמן זית", "qty": "1 tbsp", "category": "dairy_fats"},
        ],
        "prep_note_en": "Marinate chicken overnight.",
        "prep_note_he": "השרי עוף לילה שלם.",
    },
    {
        "id": "snack_001",
        "type": "snack",
        "name_en": "Apple slices",
        "name_he": "פרוסות תפוח",
        "kcal": 80,
        "macros": {"protein_g": 0, "carbs_g": 20, "fat_g": 0},
        "cooking_time": "quick",
        "positive_tags": ["kosher", "vegan", "gluten-free", "dairy-free"],
        "ingredient_flags": [],
        "ingredients": [
            {"item_en": "Apple", "item_he": "תפוח", "qty": "1 large", "category": "vegetables"},
        ],
        "prep_note_en": None,
        "prep_note_he": None,
    },
    {
        "id": "dinner_002",
        "type": "dinner",
        "name_en": "Chicken with cream sauce",
        "name_he": "עוף ברוטב שמנת",
        "kcal": 620,
        "macros": {"protein_g": 40, "carbs_g": 12, "fat_g": 30},
        "cooking_time": "medium",
        "positive_tags": [],
        "ingredient_flags": ["contains_meat", "contains_dairy"],
        "ingredients": [
            {"item_en": "Chicken", "item_he": "עוף", "qty": "200g", "category": "protein"},
            {"item_en": "Heavy cream", "item_he": "שמנת", "qty": "100ml", "category": "dairy_fats"},
        ],
        "prep_note_en": None,
        "prep_note_he": None,
    },
]


@pytest.fixture()
def pool_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    p = tmp_path / "meal_pool.json"
    p.write_text(json.dumps(POOL_FIXTURE), encoding="utf-8")
    import web.meal_selector as ms
    monkeypatch.setattr(ms, "_POOL_PATH", p)
    ms._POOL_CACHE.clear()
    return p


def test_load_pool(pool_file: Path) -> None:
    from web.meal_selector import load_pool
    pool = load_pool()
    assert len(pool) == 5
    assert pool[0]["id"] == "breakfast_001"


def test_filter_removes_pork_for_kosher(pool_file: Path) -> None:
    from web.meal_selector import filter_pool
    allergies = ["kosher"]
    result = filter_pool(POOL_FIXTURE, allergies=allergies, cooking_time="medium")
    ids = [m["id"] for m in result]
    assert "lunch_001" not in ids  # contains_pork
    assert "breakfast_001" in ids


def test_filter_removes_meat_dairy_combo_for_kosher(pool_file: Path) -> None:
    from web.meal_selector import filter_pool
    result = filter_pool(POOL_FIXTURE, allergies=["kosher"], cooking_time="medium")
    ids = [m["id"] for m in result]
    assert "dinner_002" not in ids  # meat + dairy


def test_filter_removes_dairy_allergy(pool_file: Path) -> None:
    from web.meal_selector import filter_pool
    result = filter_pool(POOL_FIXTURE, allergies=["dairy"], cooking_time="medium")
    ids = [m["id"] for m in result]
    assert "breakfast_001" not in ids  # contains_dairy
    assert "dinner_001" in ids


def test_filter_quick_excludes_elaborate(pool_file: Path) -> None:
    from web.meal_selector import filter_pool
    result = filter_pool(POOL_FIXTURE, allergies=[], cooking_time="quick")
    ids = [m["id"] for m in result]
    assert "dinner_001" not in ids  # elaborate


def test_filter_elaborate_includes_all_times(pool_file: Path) -> None:
    from web.meal_selector import filter_pool
    result = filter_pool(POOL_FIXTURE, allergies=[], cooking_time="elaborate")
    assert len(result) == 5  # all included


def test_build_selection_prompt(pool_file: Path) -> None:
    from web.meal_selector import build_selection_prompt
    prompt = build_selection_prompt(
        eligible=POOL_FIXTURE,
        goals=["build_muscle"],
        meals_per_day=3,
        week_dates=["2026-04-13", "2026-04-14"],
    )
    assert "breakfast_001 Shakshuka" in prompt
    assert "dinner_001 Grilled chicken" in prompt
    assert "meal_id" in prompt


def test_resolve_schedule(pool_file: Path) -> None:
    from web.meal_selector import resolve_schedule
    pool_by_id = {m["id"]: m for m in POOL_FIXTURE}
    schedule = {
        "days": [
            {"date": "2026-04-13", "meals": [
                {"type": "breakfast", "meal_id": "breakfast_001"},
                {"type": "dinner", "meal_id": "dinner_001"},
            ]},
        ]
    }
    resolved = resolve_schedule(schedule, pool_by_id)
    day = resolved["days"][0]
    assert day["meals"][0]["name_en"] == "Shakshuka"
    assert day["meals"][1]["name_en"] == "Grilled chicken"


def test_resolve_schedule_skips_unknown_id(pool_file: Path) -> None:
    from web.meal_selector import resolve_schedule
    pool_by_id = {m["id"]: m for m in POOL_FIXTURE}
    schedule = {
        "days": [{"date": "2026-04-13", "meals": [
            {"type": "breakfast", "meal_id": "nonexistent_999"},
        ]}]
    }
    resolved = resolve_schedule(schedule, pool_by_id)
    assert resolved["days"][0]["meals"] == []


def test_aggregate_groceries_deduplicates(pool_file: Path) -> None:
    from web.meal_selector import aggregate_groceries
    meals = [POOL_FIXTURE[0], POOL_FIXTURE[0]]  # same meal twice → eggs appear twice
    groceries = aggregate_groceries(meals, lang="en")
    egg_items = [g for g in groceries if g["item"] == "Eggs"]
    assert len(egg_items) == 1  # deduplicated


def test_aggregate_groceries_hebrew(pool_file: Path) -> None:
    from web.meal_selector import aggregate_groceries
    groceries = aggregate_groceries([POOL_FIXTURE[0]], lang="he")
    assert any(g["item"] == "ביצים" for g in groceries)


def test_extract_reminders_subtracts_one_day(pool_file: Path) -> None:
    from web.meal_selector import extract_reminders
    resolved_days = [
        {"date": "2026-04-14", "meals": [POOL_FIXTURE[2]]},  # dinner_001 has prep_note
    ]
    reminders = extract_reminders(resolved_days, lang="en")
    assert len(reminders) == 1
    # reminder fires the day before
    assert reminders[0]["day"] == "2026-04-13"
    assert "Marinate" in reminders[0]["text"]


def test_extract_reminders_hebrew(pool_file: Path) -> None:
    from web.meal_selector import extract_reminders
    resolved_days = [
        {"date": "2026-04-14", "meals": [POOL_FIXTURE[2]]},
    ]
    reminders = extract_reminders(resolved_days, lang="he")
    assert "השרי" in reminders[0]["text"]


def test_extract_reminders_caps_at_three(pool_file: Path) -> None:
    from web.meal_selector import extract_reminders
    # dinner_001 has prep_note; repeat it across 4 days
    resolved_days = [
        {"date": f"2026-04-{14 + i}", "meals": [POOL_FIXTURE[2]]}
        for i in range(4)
    ]
    reminders = extract_reminders(resolved_days, lang="en")
    assert len(reminders) <= 3
