"""
Shared onboarding questionnaire route:
  GET  /onboarding — render questionnaire (guest or logged-in)
  POST /onboarding — save answers (guest → session; logged-in → DB + auto-program)
"""

from __future__ import annotations

import json
import logging
import os

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from web.auth_utils import get_current_user, hash_password, login_session, maybe_migrate_file_token
from web.db import get_db
from web.models import Program, User
from web.program_generator import auto_generate_program
from web.rendering import render_template
from web.workout_generator import EQUIPMENT_OPTIONS

logger = logging.getLogger(__name__)
router = APIRouter()

# Goal options — label field is a translation key resolved in the template via t()
GOAL_OPTIONS = [
    {"value": "burn_fat", "label": "goal_label_burn_fat", "image": "/static/img/burn-fat.webp"},
    {
        "value": "lose_weight",
        "label": "goal_label_lose_weight",
        "image": "/static/img/lose-weight.webp",
    },
    {
        "value": "build_muscle",
        "label": "goal_label_build_muscle",
        "image": "/static/img/build-mucsle.webp",
    },
    {
        "value": "build_strength",
        "label": "goal_label_build_strength",
        "image": "/static/img/build-strength.webp",
    },
    {
        "value": "general_fitness",
        "label": "goal_label_general_fitness",
        "image": "/static/img/general-fitness.webp",
    },
    {
        "value": "endurance",
        "label": "goal_label_endurance",
        "image": "/static/img/muscular-endurance.webp",
    },
]

AGE_RANGES = ["18-29", "30-39", "40-49", "50+"]

DIET_OPTIONS = [
    {"value": "general", "label": "diet_general"},
    {"value": "vegetarian", "label": "diet_vegetarian"},
    {"value": "vegan", "label": "diet_vegan"},
    {"value": "keto", "label": "diet_keto"},
    {"value": "paleo", "label": "diet_paleo"},
    {"value": "mediterranean", "label": "diet_mediterranean"},
    {"value": "gluten_free", "label": "diet_gluten_free"},
    {"value": "high_protein", "label": "diet_high_protein"},
]

HEALTH_OPTIONS = [
    {"value": "heart_condition", "label": "health_heart_condition"},
    {"value": "diabetes", "label": "health_diabetes"},
    {"value": "high_blood_pressure", "label": "health_high_blood_pressure"},
    {"value": "joint_problems", "label": "health_joint_problems"},
    {"value": "back_pain", "label": "health_back_pain"},
    {"value": "asthma", "label": "health_asthma"},
]

FITNESS_LEVELS = [
    {"value": "Beginner", "label": "fitness_beginner", "desc": "fitness_beginner_desc"},
    {"value": "Intermediate", "label": "fitness_intermediate", "desc": "fitness_intermediate_desc"},
    {"value": "Advanced", "label": "fitness_advanced", "desc": "fitness_advanced_desc"},
]

DAYS_OF_WEEK = [
    {"value": "Sun", "label": "day_sun"},
    {"value": "Mon", "label": "day_mon"},
    {"value": "Tue", "label": "day_tue"},
    {"value": "Wed", "label": "day_wed"},
    {"value": "Thu", "label": "day_thu"},
    {"value": "Fri", "label": "day_fri"},
    {"value": "Sat", "label": "day_sat"},
]


def _decode(val: str | None) -> list:  # type: ignore[type-arg]
    if not val:
        return []
    try:
        return json.loads(val)
    except Exception:
        return []


def _parse_float(val: str | None) -> float | None:
    if not val:
        return None
    try:
        return float(val)
    except ValueError:
        return None


_FITNESS_RANK_BASE: dict[str, float] = {
    "beginner": 2.0,
    "intermediate": 5.0,
    "advanced": 8.0,
}


def compute_initial_rank(
    fitness_level: str | None,
    age_range: str | None,
    health_conditions: list[str],
) -> float:
    """Compute the starting fitness rank (1.0–10.0) from questionnaire answers."""
    base = _FITNESS_RANK_BASE.get((fitness_level or "").lower(), 3.0)
    age_penalty = -1.0 if age_range == "50+" else 0.0
    health_penalty = -0.5 if health_conditions else 0.0
    return max(1.0, min(10.0, base + age_penalty + health_penalty))


def _apply_answers(user: User, answers: dict) -> None:  # type: ignore[type-arg]
    """Write parsed questionnaire answers onto a User ORM object (does not commit)."""
    user.fitness_goals_json = answers.get("fitness_goals_json")  # type: ignore[assignment]
    user.age_range = answers.get("age_range") or None  # type: ignore[assignment]
    user.fitness_level = answers.get("fitness_level") or None  # type: ignore[assignment]
    user.preferred_days_json = answers.get("preferred_days_json")  # type: ignore[assignment]
    user.preferred_equipment_json = answers.get("preferred_equipment_json")  # type: ignore[assignment]
    user.height_cm = answers.get("height_cm")  # type: ignore[assignment]
    user.weight_kg = answers.get("weight_kg")  # type: ignore[assignment]
    user.diet_json = answers.get("diet_json")  # type: ignore[assignment]
    user.health_conditions_json = answers.get("health_conditions_json")  # type: ignore[assignment]

    # Compute fitness rank from questionnaire (always recompute on questionnaire save/retake)
    _conditions = json.loads(user.health_conditions_json or "[]")
    user.fitness_rank = compute_initial_rank(  # type: ignore[assignment]
        user.fitness_level, user.age_range, _conditions
    )


def _questionnaire_context(user: User | None, pending: dict) -> dict:  # type: ignore[type-arg]
    """Build the template context dict for the questionnaire page."""
    google_enabled = bool(
        os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET")
    )
    return dict(
        goal_options=GOAL_OPTIONS,
        age_ranges=AGE_RANGES,
        fitness_levels=FITNESS_LEVELS,
        diet_options=DIET_OPTIONS,
        health_options=HEALTH_OPTIONS,
        equipment_options=EQUIPMENT_OPTIONS,
        days_of_week=DAYS_OF_WEEK,
        is_guest=(user is None),
        is_retake=(user is not None and user.questionnaire_completed),
        google_enabled=google_enabled,
        existing_goals=_decode(
            user.fitness_goals_json if user else pending.get("fitness_goals_json")
        ),
        existing_age_range=(user.age_range if user else pending.get("age_range", "")),
        existing_fitness_level=(user.fitness_level if user else pending.get("fitness_level", "")),
        existing_days=_decode(
            user.preferred_days_json if user else pending.get("preferred_days_json")
        ),
        existing_equipment=_decode(
            user.preferred_equipment_json if user else pending.get("preferred_equipment_json")
        ),
        existing_height_cm=(user.height_cm if user else pending.get("height_cm")),
        existing_weight_kg=(user.weight_kg if user else pending.get("weight_kg")),
        existing_diet=_decode(user.diet_json if user else pending.get("diet_json")),
        existing_health=_decode(
            user.health_conditions_json if user else pending.get("health_conditions_json")
        ),
    )


@router.get("/onboarding", response_class=HTMLResponse)
async def onboarding_get(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    pending = request.session.get("pending_q", {})
    ctx = _questionnaire_context(user, pending)
    return render_template("questionnaire.html", request, db=db, **ctx)


@router.post("/onboarding")
async def onboarding_post(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    user = get_current_user(request, db)

    answers: dict = {  # type: ignore[type-arg]
        "fitness_goals_json": json.dumps(form.getlist("fitness_goals")),
        "age_range": form.get("age_range", ""),
        "fitness_level": form.get("fitness_level", ""),
        "preferred_days_json": json.dumps(form.getlist("preferred_days")),
        "preferred_equipment_json": json.dumps(form.getlist("equipment")),
        "height_cm": _parse_float(form.get("height_cm")),
        "weight_kg": _parse_float(form.get("weight_kg")),
        "diet_json": json.dumps(form.getlist("diet")),
        "health_conditions_json": json.dumps(form.getlist("health_conditions")),
    }

    if user is None:
        # Guest: stash answers in session, proceed to sign-up card
        request.session["pending_q"] = {k: v for k, v in answers.items() if v is not None}
        return RedirectResponse("/register", status_code=303)

    # Logged-in: persist questionnaire answers to DB first
    _apply_answers(user, answers)
    user.questionnaire_completed = True  # type: ignore[assignment]
    db.commit()

    # Auto-generate program if user has no active program
    active = db.query(Program).filter_by(user_id=user.id, status="active").first()
    if active is None:
        try:
            auto_generate_program(user, db)
        except Exception:
            logger.exception("Failed to auto-generate program for user %s", user.id)
            request.session["flash_error"] = (
                "Profile saved, but program generation failed. Try again from your profile."
            )

    request.session["flash_success"] = "Profile updated."
    return RedirectResponse("/", status_code=303)


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, db: Session = Depends(get_db)):
    """Show the questionnaire sign-up card directly (fallback for direct /register links)."""
    user = get_current_user(request, db)
    if user:
        return RedirectResponse("/", status_code=303)
    pending = request.session.get("pending_q", {})
    ctx = _questionnaire_context(None, pending)
    ctx["start_at_signup"] = True
    return render_template("questionnaire.html", request, db=db, **ctx)


@router.post("/register", response_model=None)
async def register_from_questionnaire(
    request: Request,
    db: Session = Depends(get_db),
) -> RedirectResponse | HTMLResponse:
    """Create account from the questionnaire sign-up card."""
    form = await request.form()
    email = str(form.get("email", "")).strip().lower()
    password = str(form.get("password", ""))
    display_name = str(form.get("display_name", "")).strip() or None

    def _err(msg: str) -> HTMLResponse:
        pending = request.session.get("pending_q", {})
        ctx = _questionnaire_context(None, pending)
        ctx["start_at_signup"] = True
        ctx["flash_error"] = msg
        return render_template("questionnaire.html", request, db=db, **ctx)  # type: ignore[return-value]

    if not email or "@" not in email:
        return _err("Please enter a valid email address.")
    if len(password) < 8:
        return _err("Password must be at least 8 characters.")
    if db.query(User).filter_by(email=email).first():
        return _err("An account with this email already exists.")

    user = User(
        email=email,
        hashed_password=hash_password(password),
        display_name=display_name,
        is_verified=False,
    )
    db.add(user)
    db.flush()

    # Apply questionnaire answers from session
    pending = request.session.pop("pending_q", {})
    if pending:
        _apply_answers(user, pending)
    user.questionnaire_completed = True  # type: ignore[assignment]

    db.commit()
    db.refresh(user)

    maybe_migrate_file_token(user, db)
    login_session(request, user, db)

    try:
        auto_generate_program(user, db)
    except Exception:
        logger.exception("Failed to auto-generate program on registration for user %s", user.id)
        request.session["flash_error"] = (
            "Account created! Program generation failed — visit your profile to set up your plan."
        )

    return RedirectResponse("/", status_code=303)
