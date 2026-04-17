"""
User-specific routes for saved plans and workout progress:
  GET    /my/plans              — list saved plans
  POST   /my/plans              — save a plan (JSON body)
  DELETE /my/plans/{id}         — delete a saved plan
  GET    /my/plans/{id}/preview — load a saved plan into the preview page
  GET    /my/progress           — workout session history
  POST   /my/sessions           — log a completed session (called by Workout Player)
"""

from __future__ import annotations

import dataclasses
import json
import logging
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from web.auth_utils import require_user
from web.db import get_db
from web.models import ProgramSession, RankFeedback, SavedPlan, WorkoutSession
from web.program_generator import refresh_future_program_sessions
from web.rendering import render_template
from web.translations import make_t
from web.workout_generator import (
    EQUIPMENT_OPTIONS,
    GOALS,
    ExerciseInfo,
    WorkoutPlan,
    _LOCAL_VIDEO_MAP,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/my")


_require_user = require_user


# ---------------------------------------------------------------------------
# Questionnaire data constants
# ---------------------------------------------------------------------------

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

GOAL_OPTIONS = [
    {"value": "lose_weight", "label": "qgoal_lose_weight"},
    {"value": "build_muscle", "label": "qgoal_build_muscle"},
    {"value": "improve_endurance", "label": "qgoal_improve_endurance"},
    {"value": "flexibility", "label": "qgoal_flexibility"},
    {"value": "general_health", "label": "qgoal_general_health"},
]

FITNESS_LEVELS = [
    {"value": "Beginner", "key": "fitness_beginner"},
    {"value": "Intermediate", "key": "fitness_intermediate"},
    {"value": "Advanced", "key": "fitness_advanced"},
]

# Maps stored fitness_level value → translation key (for profile display)
FITNESS_LEVEL_KEYS = {lvl["value"]: lvl["key"] for lvl in FITNESS_LEVELS}


def _decode_json_field(val: str | None) -> list[Any]:
    if not val:
        return []
    try:
        return json.loads(val)
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Questionnaire routes — now handled by /onboarding
# ---------------------------------------------------------------------------


@router.get("/questionnaire")
async def questionnaire_page(request: Request):
    return RedirectResponse("/onboarding", status_code=301)


@router.post("/questionnaire")
async def questionnaire_redirect_post(request: Request):
    return RedirectResponse("/onboarding", status_code=303)


# ---------------------------------------------------------------------------
# Profile page
# ---------------------------------------------------------------------------


def _build_strava_profile_ctx(user: "Any") -> dict[str, Any]:
    """Build Strava-related context for the profile template."""
    import json as _json
    from web.strava_insights import recovery_score

    strava_connected = bool(user.strava_token_json)
    strava_recovery = None

    if strava_connected and user.strava_activities_json:
        try:
            activities = _json.loads(user.strava_activities_json)
            if activities:
                strava_recovery = recovery_score(activities)
        except Exception:
            pass

    return {
        "strava_connected": strava_connected,
        "strava_athlete_id": user.strava_athlete_id,
        "strava_synced_at": user.strava_synced_at,
        "strava_recovery": strava_recovery,
    }


@router.get("/profile", response_class=HTMLResponse)
async def my_profile(request: Request, db: Session = Depends(get_db)):
    user = _require_user(request, db)
    if user is None:
        return RedirectResponse("/auth/login-forge", status_code=303)

    # Build translated label maps for the active language
    from web.translations import SUPPORTED_LANGS

    lang = "en"
    if user.preferred_lang in SUPPORTED_LANGS:
        lang = user.preferred_lang  # type: ignore[assignment]
    else:
        raw = request.session.get("lang", "en")
        if raw in SUPPORTED_LANGS:
            lang = raw
    t = make_t(lang)

    diet_labels = {o["value"]: t(o["label"]) for o in DIET_OPTIONS}
    health_labels = {o["value"]: t(o["label"]) for o in HEALTH_OPTIONS}
    goal_labels = {o["value"]: t(o["label"]) for o in GOAL_OPTIONS}
    eq_labels = {eq["tag"]: f"{eq['icon']} {eq['label']}" for eq in EQUIPMENT_OPTIONS}

    strava_ctx = _build_strava_profile_ctx(user)

    return render_template(
        "my_profile.html",
        request,
        db=db,
        diet_labels=diet_labels,
        health_labels=health_labels,
        goal_labels=goal_labels,
        eq_labels=eq_labels,
        fitness_level_keys=FITNESS_LEVEL_KEYS,
        user_diet=_decode_json_field(user.diet_json),
        user_health=_decode_json_field(user.health_conditions_json),
        user_goals=_decode_json_field(user.fitness_goals_json),
        user_equipment=_decode_json_field(user.preferred_equipment_json),
        **strava_ctx,
    )


# ---------------------------------------------------------------------------
# Saved plans
# ---------------------------------------------------------------------------


@router.get("/plans", response_class=HTMLResponse)
async def my_plans(request: Request, db: Session = Depends(get_db)):
    user = _require_user(request, db)
    if user is None:
        return RedirectResponse("/auth/login-forge", status_code=303)
    plans = (
        db.query(SavedPlan)
        .options(joinedload(SavedPlan.program_session).joinedload(ProgramSession.program))
        .filter_by(user_id=user.id)
        .order_by(SavedPlan.created_at.desc())
        .all()
    )
    goal_icons = {k: v["icon"] for k, v in GOALS.items()}
    return render_template("my_plans.html", request, db=db, plans=plans, goal_icons=goal_icons)


@router.post("/plans")
async def save_plan(request: Request, db: Session = Depends(get_db)):
    user = _require_user(request, db)
    if user is None:
        return JSONResponse({"ok": False, "error": "Not authenticated"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "Invalid JSON"}, status_code=400)

    required = {"name", "goal", "duration_minutes", "exercises", "garmin_payload"}
    missing = required - body.keys()
    if missing:
        return JSONResponse({"ok": False, "error": f"Missing fields: {missing}"}, status_code=400)

    plan = SavedPlan(
        user_id=user.id,
        name=str(body["name"])[:200],
        goal=str(body["goal"])[:50],
        equipment_json=json.dumps(body.get("equipment", [])),
        duration_minutes=int(body["duration_minutes"]),
        exercises_json=json.dumps(body["exercises"]),
        garmin_payload_json=json.dumps(body["garmin_payload"]),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return {"ok": True, "id": plan.id}


@router.delete("/plans/{plan_id}")
async def delete_plan(plan_id: str, request: Request, db: Session = Depends(get_db)):
    user = _require_user(request, db)
    if user is None:
        return JSONResponse({"ok": False, "error": "Not authenticated"}, status_code=401)

    plan = db.query(SavedPlan).filter_by(id=plan_id, user_id=user.id).first()
    if plan is None:
        return JSONResponse({"ok": False, "error": "Plan not found"}, status_code=404)

    db.delete(plan)
    db.commit()
    return {"ok": True}


@router.get("/plans/{plan_id}/preview", response_class=HTMLResponse)
async def load_plan_preview(plan_id: str, request: Request, db: Session = Depends(get_db)):
    user = _require_user(request, db)
    if user is None:
        return RedirectResponse("/auth/login-forge", status_code=303)

    plan = db.query(SavedPlan).filter_by(id=plan_id, user_id=user.id).first()
    if plan is None:
        request.session["flash_error"] = "Plan not found."
        return RedirectResponse("/my/plans", status_code=303)

    equipment = json.loads(plan.equipment_json)
    exercises = [ExerciseInfo(**e) for e in json.loads(plan.exercises_json)]
    goal_cfg = GOALS.get(plan.goal, {})

    workout_plan = WorkoutPlan(
        name=plan.name,
        goal_label=goal_cfg.get("label", plan.goal),
        goal_icon=goal_cfg.get("icon", "🏋️"),
        description=goal_cfg.get("description", ""),
        duration_minutes=plan.duration_minutes,
        exercises=exercises,
        garmin_payload=json.loads(plan.garmin_payload_json),
    )

    return render_template(
        "workout_preview.html",
        request,
        db=db,
        plan=workout_plan,
        payload_json=plan.garmin_payload_json,
        exercises_list=json.loads(plan.exercises_json),
        video_map_json=json.dumps(_LOCAL_VIDEO_MAP),
        goals=GOALS,
        equipment_options=EQUIPMENT_OPTIONS,
        selected_goal=plan.goal,
        selected_duration=plan.duration_minutes,
        selected_equipment=equipment,
    )


# ---------------------------------------------------------------------------
# Progress / session logging
# ---------------------------------------------------------------------------


@router.get("/progress", response_class=HTMLResponse)
async def my_progress(request: Request, db: Session = Depends(get_db)):
    user = _require_user(request, db)
    if user is None:
        return RedirectResponse("/auth/login-forge", status_code=303)

    sessions = (
        db.query(WorkoutSession)
        .filter_by(user_id=user.id)
        .order_by(WorkoutSession.started_at.desc())
        .limit(100)
        .all()
    )
    rated_session_ids: set[str] = {
        rf.session_id
        for rf in db.query(RankFeedback)
        .filter(
            RankFeedback.user_id == user.id,
            RankFeedback.trigger == "post_workout",
            RankFeedback.session_id.isnot(None),
        )
        .all()
    }
    return render_template(
        "my_progress.html",
        request,
        db=db,
        sessions=sessions,
        rated_session_ids=rated_session_ids,
    )


@router.post("/sessions")
async def log_session(request: Request, db: Session = Depends(get_db)):
    user = _require_user(request, db)
    if user is None:
        return JSONResponse({"ok": False, "error": "Not authenticated"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "Invalid JSON"}, status_code=400)

    if "plan_name" not in body or "started_at" not in body:
        return JSONResponse(
            {"ok": False, "error": "Missing plan_name or started_at"}, status_code=400
        )

    try:
        started_at = datetime.fromisoformat(body["started_at"])
    except (ValueError, TypeError):
        return JSONResponse({"ok": False, "error": "Invalid started_at format"}, status_code=400)

    completed_at = None
    if body.get("completed_at"):
        try:
            completed_at = datetime.fromisoformat(body["completed_at"])
        except (ValueError, TypeError):
            pass

    session_row = WorkoutSession(
        user_id=user.id,
        plan_id=body.get("plan_id") or None,
        plan_name=str(body["plan_name"])[:200],
        started_at=started_at,
        completed_at=completed_at,
        exercises_completed=int(body.get("exercises_completed", 0)),
        total_exercises=int(body.get("total_exercises", 0)),
        rounds_completed=int(body.get("rounds_completed", 0)),
        total_rounds=int(body.get("total_rounds", 0)),
        notes=body.get("notes") or None,
    )
    db.add(session_row)
    db.commit()
    db.refresh(session_row)
    return {"ok": True, "id": session_row.id}


# ---------------------------------------------------------------------------
# Rank feedback
# ---------------------------------------------------------------------------

_RANK_DELTAS: dict[tuple[str, str], float] = {
    ("mid_workout", "too_easy"): +0.1,
    ("mid_workout", "too_hard"): -0.1,
    ("post_workout", "too_easy"): +0.5,
    ("post_workout", "just_right"): 0.0,
    ("post_workout", "too_hard"): -0.5,
}


class RankFeedbackRequest(BaseModel):
    trigger: Literal["mid_workout", "post_workout"]
    feedback: Literal["too_easy", "just_right", "too_hard"]
    session_id: str | None = None


@router.patch("/rank-feedback")
async def rank_feedback(
    body: RankFeedbackRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, float]:
    user = _require_user(request, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    key = (body.trigger, body.feedback)
    if key not in _RANK_DELTAS:
        raise HTTPException(
            status_code=400, detail="'just_right' feedback is only valid for post_workout"
        )

    delta = _RANK_DELTAS[key]

    if body.session_id is not None:
        session_exists = (
            db.query(WorkoutSession).filter_by(id=body.session_id, user_id=user.id).first()
        )
        if session_exists is None:
            raise HTTPException(status_code=400, detail="session_id not found")

    rank_before = user.fitness_rank if user.fitness_rank is not None else 3.0
    rank_after = max(1.0, min(10.0, rank_before + delta))

    user.fitness_rank = rank_after

    rf = RankFeedback(
        user_id=user.id,
        session_id=body.session_id,
        trigger=body.trigger,
        feedback=body.feedback,
        delta=delta,
        rank_before=rank_before,
        rank_after=rank_after,
    )
    db.add(rf)
    db.flush()

    # Regenerate future program sessions to reflect the new fitness rank
    refreshed = refresh_future_program_sessions(user, db)
    if refreshed:
        logger.info(
            "Refreshed %d future program sessions for user %s (rank %.1f → %.1f)",
            refreshed,
            user.id,
            rank_before,
            rank_after,
        )

    db.commit()

    return {"rank_before": rank_before, "rank_after": rank_after, "sessions_refreshed": refreshed}


# ---------------------------------------------------------------------------
# Utility: serialise ExerciseInfo for template use
# ---------------------------------------------------------------------------


def exercises_to_json(exercises: list[ExerciseInfo]) -> str:
    return json.dumps([dataclasses.asdict(e) for e in exercises])
