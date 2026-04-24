"""
Nutrition plan generator for GarminForge.

Entry point: generate_weekly_plan(user, db) -> NutritionPlan
Lazy strategy: returns cached plan for current week if already ready.

Uses the meal pool: Claude selects meal IDs from a filtered list;
groceries and reminders are computed deterministically from pool data.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from web.ai_provider import get_ai_provider
from web.meal_selector import (
    aggregate_groceries,
    build_selection_prompt,
    extract_reminders,
    filter_pool,
    load_pool,
    resolve_schedule,
)
from web.models import MealSuggestion, Notification, NutritionPlan, User

logger = logging.getLogger(__name__)

# Kept for backward compat with existing tests that import it
PLAN_SCHEMA_EXAMPLE = """{
  "days": [
    {
      "date": "YYYY-MM-DD",
      "meals": [
        {
          "type": "breakfast|lunch|dinner|snack",
          "name": "Meal name",
          "kcal": 420,
          "macros": {"protein_g": 22, "carbs_g": 9, "fat_g": 20}
        }
      ]
    }
  ]
}"""


def last_sunday(today: date) -> date:
    """Return the most recent Sunday (inclusive of today if today is Sunday)."""
    days_back = today.isoweekday() % 7  # Sun=0, Mon=1, ..., Sat=6
    return date.fromordinal(today.toordinal() - days_back)


def _user_context(user: User) -> tuple[dict[str, Any], list[str], list[str], list[str], str]:
    """Extract commonly needed user fields."""
    profile: dict[str, Any] = json.loads(user.nutrition_profile_json or "{}")
    diet: list[str] = json.loads(user.diet_json or "[]")
    goals: list[str] = json.loads(user.fitness_goals_json or "[]")
    health: list[str] = json.loads(user.health_conditions_json or "[]")
    lang = user.preferred_lang or "en"
    return profile, diet, goals, health, lang


def _get_eligible_meals(user: User, db: Session) -> list[dict[str, Any]]:
    """Return pool meals filtered for this user, merged with their pending suggestions."""
    profile, _, _, _, _ = _user_context(user)
    allergies: list[str] = profile.get("allergies", [])
    cooking_time: str = profile.get("cooking_time", "medium")

    pool = load_pool()
    eligible = filter_pool(pool, allergies=allergies, cooking_time=cooking_time)

    # Merge user's pending suggestions
    suggestions = (
        db.query(MealSuggestion)
        .filter_by(user_id=user.id, status="pending")
        .all()
    )
    for suggestion in suggestions:
        try:
            meal = json.loads(suggestion.meal_json)
            filtered = filter_pool([meal], allergies=allergies, cooking_time=cooking_time)
            eligible.extend(filtered)
        except Exception as exc:
            logger.warning("Could not parse MealSuggestion %s: %s", suggestion.id, exc)

    return eligible


def _build_plan_json(
    resolved: dict[str, Any],
    lang: str,
) -> dict[str, Any]:
    """Convert resolved schedule (with full meal objects) to the template-compatible plan_json format."""
    name_key = "name_he" if lang == "he" else "name_en"

    days_out: list[dict[str, Any]] = []
    all_meals: list[dict[str, Any]] = []

    for day in resolved.get("days", []):
        meals_out = []
        for meal in day.get("meals", []):
            meals_out.append({
                "type": meal.get("type", ""),
                "name": meal.get(name_key, meal.get("name_en", "")),
                "kcal": meal.get("kcal"),
                "macros": meal.get("macros"),
            })
            all_meals.append(meal)
        days_out.append({"date": day["date"], "meals": meals_out})

    groceries = aggregate_groceries(all_meals, lang=lang)
    reminders = extract_reminders(resolved.get("days", []), lang=lang)

    return {"days": days_out, "groceries": groceries, "reminders": reminders}


def generate_weekly_plan(user: User, db: Session) -> NutritionPlan:
    """Return this week's NutritionPlan, generating lazily if needed."""
    week_start = last_sunday(date.today())

    existing = (
        db.query(NutritionPlan)
        .filter_by(user_id=user.id, week_start=week_start, status="ready")
        .first()
    )
    if existing:
        return existing

    db.query(NutritionPlan).filter_by(user_id=user.id, week_start=week_start).delete()
    plan = NutritionPlan(user_id=user.id, week_start=week_start, status="generating")
    db.add(plan)
    db.commit()
    db.refresh(plan)

    try:
        profile, diet, goals, health, lang = _user_context(user)
        eligible = _get_eligible_meals(user, db)

        week_dates = [
            str(date.fromordinal(week_start.toordinal() + i)) for i in range(7)
        ]

        prompt = build_selection_prompt(
            eligible=eligible,
            goals=goals + diet + health,
            meals_per_day=profile.get("meals_per_day", 3),
            week_dates=week_dates,
        )

        raw = get_ai_provider().complete(prompt)
        logger.info("Selection response (first 400 chars): %s", raw[:400])

        schedule: Any = json.loads(raw)
        if not isinstance(schedule, dict) or "days" not in schedule:
            raise ValueError(f"Selection response missing 'days' key. Got: {raw[:200]}")

        pool_by_id = {m["id"]: m for m in eligible}
        resolved = resolve_schedule(schedule, pool_by_id)

        plan_data = _build_plan_json(resolved, lang=lang)
        plan.plan_json = json.dumps(plan_data)
        plan.status = "ready"
        plan.generated_at = datetime.utcnow()
        db.commit()

        # Create Notification rows for reminders
        for reminder in plan_data.get("reminders", []):
            day_str: str = reminder.get("day", "")
            body: str = reminder.get("text", "")
            if not day_str or not body:
                continue
            try:
                d = date.fromisoformat(day_str)
                scheduled = datetime(d.year, d.month, d.day, 18, 0)
            except ValueError:
                continue
            db.add(Notification(
                user_id=user.id,
                nutrition_plan_id=plan.id,
                scheduled_for=scheduled,
                channel="both",
                title_key="reminder_prep_title",
                body=body,
            ))
        db.commit()

    except Exception as exc:
        logger.error("Nutrition plan generation failed: %s", exc)
        plan.status = "error"
        db.commit()

    db.refresh(plan)
    return plan


def get_todays_meals(plan: NutritionPlan, today: date | None = None) -> list[dict[str, Any]]:
    """Return the meal list for today from a ready plan."""
    if plan.status != "ready" or not plan.plan_json:
        return []
    today_str = str(today or date.today())
    plan_data: dict[str, Any] = json.loads(plan.plan_json)
    for day in plan_data.get("days", []):
        if day.get("date") == today_str:
            return list(day.get("meals", []))
    return []


def get_todays_reminder(plan: NutritionPlan, today: date | None = None) -> str | None:
    """Return the first reminder text for today, or None."""
    if plan.status != "ready" or not plan.plan_json:
        return None
    today_str = str(today or date.today())
    plan_data: dict[str, Any] = json.loads(plan.plan_json)
    for reminder in plan_data.get("reminders", []):
        if reminder.get("day") == today_str:
            return str(reminder.get("text", ""))
    return None
