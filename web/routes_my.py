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

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from web.auth_utils import get_current_user
from web.db import get_db
from web.models import SavedPlan, WorkoutSession
from web.rendering import render_template
from web.workout_generator import EQUIPMENT_OPTIONS, GOALS, ExerciseInfo, WorkoutPlan

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/my")


def _require_user(request: Request, db: Session):
    """Return current user or raise a redirect to login."""
    user = get_current_user(request, db)
    if not user:
        return None
    return user


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
        .filter_by(user_id=user.id)
        .order_by(SavedPlan.created_at.desc())
        .all()
    )
    goal_icons = {k: v["icon"] for k, v in GOALS.items()}
    return render_template(
        "my_plans.html", request, db=db, plans=plans, goal_icons=goal_icons
    )


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
        exercises_json=plan.exercises_json,
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
    return render_template("my_progress.html", request, db=db, sessions=sessions)


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
        return JSONResponse({"ok": False, "error": "Missing plan_name or started_at"}, status_code=400)

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
# Utility: serialise ExerciseInfo for template use
# ---------------------------------------------------------------------------


def exercises_to_json(exercises: list[ExerciseInfo]) -> str:
    return json.dumps([dataclasses.asdict(e) for e in exercises])
