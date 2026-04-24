"""
Meal pool selector for GarminForge nutrition plans.

Public API:
  load_pool() -> list[dict]
  filter_pool(pool, allergies, cooking_time) -> list[dict]
  build_selection_prompt(eligible, goals, meals_per_day, week_dates) -> str
  resolve_schedule(schedule, pool_by_id) -> dict
  aggregate_groceries(resolved_meals, lang) -> list[dict]
  extract_reminders(resolved_days, lang) -> list[dict]
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Module-level path (monkeypatched in tests)
_POOL_PATH = Path(__file__).parent / "data" / "meal_pool.json"

# Mutable cache — dict so tests can call .clear()
_POOL_CACHE: dict[str, list[dict[str, Any]]] = {}

# Allergy → ingredient_flag mapping
_ALLERGY_FLAGS: dict[str, str] = {
    "dairy": "contains_dairy",
    "gluten": "contains_gluten",
    "nuts": "contains_nuts",
    "eggs": "contains_eggs",
    "soy": "contains_soy",
    "shellfish": "contains_shellfish",
    "fish": "contains_fish",
}

def load_pool() -> list[dict[str, Any]]:
    """Load meal pool from JSON, caching after first load."""
    if "pool" not in _POOL_CACHE:
        with open(_POOL_PATH, encoding="utf-8") as f:
            _POOL_CACHE["pool"] = json.load(f)
    return _POOL_CACHE["pool"]


def filter_pool(
    pool: list[dict[str, Any]],
    allergies: list[str],
    cooking_time: str,
) -> list[dict[str, Any]]:
    """Return meals eligible for this user profile.

    Cooking-time filter: only ``"quick"`` is a hard constraint (non-quick meals
    are excluded).  ``"medium"`` and ``"elaborate"`` accept all cooking times —
    this is intentional so that users who can cook medium/elaborate dishes still
    see quick-prep options alongside longer ones.
    """
    kosher = "kosher" in allergies

    # Flags to exclude based on non-kosher allergies
    excluded_flags: set[str] = set()
    for allergy in allergies:
        if allergy == "kosher":
            excluded_flags.add("contains_pork")
            excluded_flags.add("contains_shellfish")
        elif allergy in _ALLERGY_FLAGS:
            excluded_flags.add(_ALLERGY_FLAGS[allergy])

    result = []
    for meal in pool:
        flags: list[str] = meal.get("ingredient_flags", [])

        # Exclude by flag
        if excluded_flags.intersection(flags):
            continue

        # Kosher: exclude meat+dairy combos
        if kosher and "contains_meat" in flags and "contains_dairy" in flags:
            continue

        # Cooking time filter: only "quick" is a hard constraint
        if cooking_time == "quick" and meal.get("cooking_time") != "quick":
            continue

        result.append(meal)

    return result


def build_selection_prompt(
    eligible: list[dict[str, Any]],
    goals: list[str],
    meals_per_day: int,
    week_dates: list[str],
) -> str:
    """Build the compact selection prompt for Claude."""
    by_type: dict[str, list[str]] = defaultdict(list)
    for meal in eligible:
        by_type[meal["type"]].append(f"{meal['id']} {meal['name_en']}")

    meal_lines = ""
    for t in ["breakfast", "lunch", "dinner", "snack"]:
        if by_type[t]:
            meal_lines += f"\n{t}: " + ", ".join(by_type[t])

    goals_str = ", ".join(goals) or "general fitness"

    return f"""Build a 7-day meal plan by selecting from the eligible meals below.

Rules:
- Select exactly {meals_per_day} meal(s) per day
- No protein source repeated more than twice in a row across any meal type
- Vary cooking methods across the week
- User goal: {goals_str}
- Week dates (Sun–Sat): {", ".join(week_dates)}

Return ONLY valid JSON — no explanation, no markdown:
{{"days":[{{"date":"YYYY-MM-DD","meals":[{{"type":"breakfast|lunch|dinner|snack","meal_id":"..."}}]}}]}}
{meal_lines}"""


def resolve_schedule(
    schedule: dict[str, Any],
    pool_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Map meal_id references to full meal objects. Unknown IDs are skipped."""
    resolved_days = []
    for day in schedule.get("days", []):
        resolved_meals = []
        for slot in day.get("meals", []):
            meal_id = slot.get("meal_id", "")
            meal = pool_by_id.get(meal_id)
            if meal is None:
                logger.warning("Unknown meal_id %r — skipping", meal_id)
                continue
            resolved_meals.append(meal)
        resolved_days.append({"date": day["date"], "meals": resolved_meals})
    return {"days": resolved_days}


def aggregate_groceries(
    meals: list[dict[str, Any]],
    lang: str,
) -> list[dict[str, Any]]:
    """Aggregate ingredients across resolved meals into a deduplicated grocery list."""
    # key: (item_name, category) → qty list
    seen: dict[tuple[str, str], list[str]] = defaultdict(list)

    for meal in meals:
        for ing in meal.get("ingredients", []):
            item = ing.get("item_he" if lang == "he" else "item_en", "")
            category = ing.get("category", "pantry")
            qty = ing.get("qty", "")
            if item:
                seen[(item, category)].append(qty)

    result = []
    for (item, category), qtys in seen.items():
        # Simple dedup: join unique quantities
        unique_qtys = list(dict.fromkeys(qtys))
        result.append({
            "item": item,
            "qty": " + ".join(unique_qtys),
            "category": category,
        })

    # Sort by category order
    cat_order = {"protein": 0, "vegetables": 1, "dairy_fats": 2, "pantry": 3}
    result.sort(key=lambda g: cat_order.get(g["category"], 9))
    return result


def extract_reminders(
    resolved_days: list[dict[str, Any]],
    lang: str,
    max_reminders: int = 3,
) -> list[dict[str, Any]]:
    """Extract prep reminders from resolved days, capped at max_reminders."""
    note_key = "prep_note_he" if lang == "he" else "prep_note_en"
    reminders: list[dict[str, Any]] = []

    for day in resolved_days:
        if len(reminders) >= max_reminders:
            break
        day_date = day.get("date", "")
        for meal in day.get("meals", []):
            note = meal.get(note_key)
            if note:
                # Reminder fires the evening before
                try:
                    d = date.fromisoformat(day_date)
                    reminder_day = str(d - timedelta(days=1))
                except ValueError:
                    continue
                reminders.append({"day": reminder_day, "text": note})
                break  # one reminder per day

    return reminders
