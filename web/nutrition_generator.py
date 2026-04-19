"""
Nutrition plan generator for GarminForge.

Entry point: generate_weekly_plan(user, db) -> NutritionPlan
Lazy strategy: returns cached plan for current week if already ready.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from web.ai_provider import get_ai_provider
from web.models import Notification, NutritionPlan, User

logger = logging.getLogger(__name__)

DAYS_SCHEMA_EXAMPLE = """{
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

GROCERIES_SCHEMA_EXAMPLE = """{
  "groceries": [
    {"item": "Chicken breast", "qty": "600g", "category": "protein|vegetables|dairy_fats|pantry"}
  ],
  "reminders": [
    {"day": "YYYY-MM-DD", "text": "Defrost chicken for tomorrow"}
  ]
}"""

# Keep for backwards compat / tests
PLAN_SCHEMA_EXAMPLE = DAYS_SCHEMA_EXAMPLE


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


def _lang_instruction(lang: str) -> str:
    if lang == "he":
        return (
            "כתוב את כל הטקסט הקריא (שמות ארוחות, מצרכים, תזכורות) בעברית. "
            "מפתחות ה-JSON חייבים להישאר באנגלית."
        )
    return (
        f"Write all human-readable text (meal names, grocery items, reminder text) in {lang}. "
        "JSON keys must stay in English."
    )


def _build_days_prompt(user: User) -> str:
    """Prompt for the meal plan only (days + meals). Kept short so small models don't truncate."""
    profile, diet, goals, health, lang = _user_context(user)

    week_start = last_sunday(date.today())
    week_dates = [str(date.fromordinal(week_start.toordinal() + i)) for i in range(7)]

    avoid_str = ", ".join(profile.get("avoid", [])) or "none"
    resist_str = ", ".join(profile.get("cant_resist", [])) or "none"
    allergy_str = ", ".join(profile.get("allergies", [])) or "none"
    calorie_mode = profile.get("calorie_mode", "macros")
    calorie_instruction = {
        "ideas": "Do NOT include kcal or macros — omit those fields entirely.",
        "macros": "Include kcal and macros (protein_g, carbs_g, fat_g) for every meal.",
        "budget": "Include kcal and macros per meal plus daily totals after the meals array.",
    }.get(calorie_mode, "Include kcal and macros for every meal.")

    return f"""You are a professional nutritionist. Generate a 7-day meal plan as valid JSON.

CRITICAL RULES:
1. Start your response with {{ and end with }}.
2. No preamble, no explanation, no markdown, no code fences. Only raw JSON.
3. The top-level object must have exactly one key: "days".

User profile:
- Diet: {", ".join(diet) or "general"}
- Goals: {", ".join(goals) or "general fitness"}
- Health conditions: {", ".join(health) or "none"}
- Allergies: {allergy_str}
- Foods to NEVER suggest: {avoid_str}
- Favourite foods (include where appropriate): {resist_str}
- Meals per day: {profile.get("meals_per_day", 3)}
- Cooking time: {profile.get("cooking_time", "medium")}
- Calorie tracking: {calorie_mode}. {calorie_instruction}

Week dates (Sunday–Saturday): {", ".join(week_dates)}
{_lang_instruction(lang)}

JSON schema:
{DAYS_SCHEMA_EXAMPLE}"""


def _build_groceries_prompt(user: User, days_json: str) -> str:
    """Prompt for groceries + reminders, given the already-generated days.
    Kept deliberately short so small models don't exceed their token budget.
    """
    profile, diet, goals, health, lang = _user_context(user)
    allergy_str = ", ".join(profile.get("allergies", [])) or "none"

    return f"""Given the meal plan below, output ONLY a JSON object with two keys: "groceries" and "reminders".

RULES:
- Start with {{ end with }}. No preamble, no markdown.
- groceries: array of max 12 items, each: {{"item":"...","qty":"...","category":"protein|vegetables|dairy_fats|pantry"}}
- reminders: array of max 3 items, each: {{"day":"YYYY-MM-DD","text":"..."}}
- Consolidate duplicate ingredients across all days.
- Allergies to exclude: {allergy_str}
- {_lang_instruction(lang)}

Meal plan (summary — use ingredient names from meals):
{days_json}

Output only the JSON object, nothing else."""


# Keep old name as alias so existing tests pass without changes
def _build_prompt(user: User) -> str:
    return _build_days_prompt(user)


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
        provider = get_ai_provider()

        # ── Call 1: meal plan (days only) ──────────────────────────────────
        days_raw = provider.complete(_build_days_prompt(user))
        logger.info("Days response (first 400 chars): %s", days_raw[:400])

        days_parsed: Any = json.loads(days_raw)
        if isinstance(days_parsed, list):
            logger.warning("Model returned bare list for days; wrapping")
            days_parsed = {"days": days_parsed}
        elif not isinstance(days_parsed, dict) or "days" not in days_parsed:
            raise ValueError(f"Days response missing 'days' key. Got: {days_raw[:200]}")

        days_list: list[dict[str, Any]] = days_parsed["days"]

        # ── Call 2: groceries + reminders ──────────────────────────────────
        groceries: list[dict[str, Any]] = []
        reminders: list[dict[str, Any]] = []
        try:
            gr_raw = provider.complete(_build_groceries_prompt(user, json.dumps({"days": days_list})))
            logger.info("Groceries response (first 400 chars): %s", gr_raw[:400])
            gr_parsed: Any = json.loads(gr_raw)
            if isinstance(gr_parsed, dict) and "groceries" in gr_parsed:
                groceries = gr_parsed.get("groceries", [])
                reminders = gr_parsed.get("reminders", [])
            elif isinstance(gr_parsed, list):
                # Model returned the groceries array directly
                groceries = gr_parsed
            elif isinstance(gr_parsed, dict) and "item" in gr_parsed:
                # Model returned a single grocery item — extraction hit inner object
                logger.warning("Groceries truncated; got single item. Storing as one-item list.")
                groceries = [gr_parsed]
            else:
                logger.warning("Groceries response unrecognised structure: %s", gr_raw[:200])
        except Exception as gr_exc:
            logger.warning("Groceries/reminders generation failed (non-fatal): %s", gr_exc)

        plan_data: dict[str, Any] = {
            "days": days_list,
            "groceries": groceries,
            "reminders": reminders,
        }
        plan.plan_json = json.dumps(plan_data)
        plan.status = "ready"
        plan.generated_at = datetime.utcnow()
        db.commit()

        for reminder in reminders:
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
