"""
Program routes for multi-week training program management:
  GET    /my/programs/new       — program creation wizard
  POST   /my/programs/preview   — generate program preview (no DB write)
  GET    /my/programs           — list user's programs
  POST   /my/programs           — create a program + all sessions atomically
  DELETE /my/programs/{id}      — delete a program (cascades to program_sessions)
  GET    /my/programs/{id}      — program detail view
"""
from __future__ import annotations

import dataclasses
import json
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from web.auth_utils import require_user
from web.db import get_db
from web.models import Program, ProgramSession
from web.program_generator import generate_program
from web.rendering import render_template
from web.workout_generator import EQUIPMENT_OPTIONS, GOALS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/my")

_require_user = require_user


# ---------------------------------------------------------------------------
# New program wizard
# ---------------------------------------------------------------------------


@router.get("/programs/new", response_class=HTMLResponse)
async def new_program_wizard(request: Request, db: Session = Depends(get_db)):
    """Render the multi-step program creation wizard, pre-filled from profile."""
    user = _require_user(request, db)
    if user is None:
        return RedirectResponse("/auth/login-forge", status_code=303)

    # Pre-fill from questionnaire answers
    profile_equipment: list[str] = json.loads(user.preferred_equipment_json or "[]")
    profile_goals: list[str] = json.loads(user.fitness_goals_json or "[]")
    profile_goal = profile_goals[0] if profile_goals else "general_fitness"
    profile_weekly_days: int = user.weekly_workout_days or 3
    profile_fitness_level: str = user.fitness_level or "intermediate"

    return render_template(
        "my_programs_new.html",
        request,
        db=db,
        goals=GOALS,
        equipment_options=EQUIPMENT_OPTIONS,
        profile_goal=profile_goal,
        profile_equipment=profile_equipment,
        profile_weekly_days=profile_weekly_days,
        profile_fitness_level=profile_fitness_level,
    )


# ---------------------------------------------------------------------------
# Preview endpoint — runs generator, returns JSON, NO DB writes
# ---------------------------------------------------------------------------


@router.post("/programs/preview")
async def preview_program(request: Request, db: Session = Depends(get_db)):
    """Generate a program preview and return it as JSON.  Nothing is saved."""
    user = _require_user(request, db)
    if user is None:
        return JSONResponse({"ok": False, "error": "Not authenticated"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "Invalid JSON"}, status_code=400)

    required = {"goal", "equipment", "duration_weeks", "weekly_workout_days", "duration_minutes",
                "periodization_type"}
    missing = required - body.keys()
    if missing:
        return JSONResponse({"ok": False, "error": f"Missing fields: {missing}"}, status_code=400)

    try:
        plan = generate_program(
            goal=str(body["goal"]),
            equipment=list(body.get("equipment") or []),
            duration_weeks=int(body["duration_weeks"]),
            weekly_workout_days=int(body["weekly_workout_days"]),
            duration_minutes=int(body["duration_minutes"]),
            periodization_type=str(body["periodization_type"]),
            fitness_level=str(body.get("fitness_level") or "intermediate"),
        )
    except ValueError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    # Serialize the ProgramPlan to JSON-safe dict.
    # sessions contain ExerciseInfo dataclasses + raw dicts (garmin_payload).
    sessions_data = []
    for s in plan.sessions:
        sessions_data.append({
            "week_num": s.week_num,
            "day_num": s.day_num,
            "focus": s.focus,
            "workout_name": s.workout_name,
            "phase": s.phase,
            "sets": s.sets,
            "reps_low": s.reps_low,
            "reps_high": s.reps_high,
            "rest_seconds": s.rest_seconds,
            "exercises": [dataclasses.asdict(ex) for ex in s.exercises],
            "garmin_payload": s.garmin_payload,
        })

    return JSONResponse({
        "ok": True,
        "program": {
            "name": plan.name,
            "goal": plan.goal,
            "goal_label": plan.goal_label,
            "goal_icon": plan.goal_icon,
            "periodization_type": plan.periodization_type,
            "duration_weeks": plan.duration_weeks,
            "weekly_workout_days": plan.weekly_workout_days,
            "duration_minutes": plan.duration_minutes,
            "equipment": plan.equipment,
            "sessions": sessions_data,
        },
    })


# ---------------------------------------------------------------------------
# List programs
# ---------------------------------------------------------------------------


@router.get("/programs", response_class=HTMLResponse)
async def list_programs(request: Request, db: Session = Depends(get_db)):
    user = _require_user(request, db)
    if user is None:
        return RedirectResponse("/auth/login-forge", status_code=303)
    programs = (
        db.query(Program)
        .filter_by(user_id=user.id)
        .order_by(Program.created_at.desc())
        .all()
    )
    goal_icons = {k: v["icon"] for k, v in GOALS.items()}
    return render_template(
        "my_programs.html", request, db=db, programs=programs, goal_icons=goal_icons
    )


# ---------------------------------------------------------------------------
# Create program — saves Program + all ProgramSession rows atomically
# ---------------------------------------------------------------------------


@router.post("/programs")
async def create_program(request: Request, db: Session = Depends(get_db)):
    """Create a Program and optionally all its ProgramSession rows in one transaction.

    When ``sessions`` is provided in the request body (from the preview step),
    all sessions are written atomically with the Program record.
    When ``sessions`` is absent, a shell Program is created (legacy behaviour).
    """
    user = _require_user(request, db)
    if user is None:
        return JSONResponse({"ok": False, "error": "Not authenticated"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "Invalid JSON"}, status_code=400)

    required = {"name", "goal", "periodization_type", "duration_weeks", "equipment"}
    missing = required - body.keys()
    if missing:
        return JSONResponse({"ok": False, "error": f"Missing fields: {missing}"}, status_code=400)

    goal = str(body["goal"])
    if goal not in GOALS:
        return JSONResponse({"ok": False, "error": f"Invalid goal: {goal!r}"}, status_code=400)

    periodization_type = str(body["periodization_type"])
    if periodization_type not in {"linear", "undulating", "block"}:
        return JSONResponse(
            {"ok": False, "error": f"Invalid periodization_type: {periodization_type!r}"},
            status_code=400,
        )

    try:
        duration_weeks = int(body["duration_weeks"])
        if not 1 <= duration_weeks <= 52:
            raise ValueError
    except (TypeError, ValueError):
        return JSONResponse(
            {"ok": False, "error": "duration_weeks must be an integer between 1 and 52"},
            status_code=400,
        )

    equipment = body.get("equipment") or []
    program = Program(
        user_id=user.id,
        name=str(body["name"])[:200],
        goal=goal,
        periodization_type=periodization_type,
        duration_weeks=duration_weeks,
        equipment_json=json.dumps(equipment) if not isinstance(equipment, str) else equipment,
        status="active",
    )
    db.add(program)
    db.flush()  # assign program.id without committing yet

    # If sessions were provided (from preview step), persist them now
    sessions_data: list[dict] = body.get("sessions") or []
    for s in sessions_data:
        program_session = ProgramSession(
            program_id=program.id,
            week_num=int(s["week_num"]),
            day_num=int(s["day_num"]),
            focus=str(s["focus"])[:100],
            garmin_payload_json=json.dumps(s["garmin_payload"]),
            exercises_json=json.dumps(s["exercises"]),
        )
        db.add(program_session)

    db.commit()
    db.refresh(program)
    return JSONResponse({"ok": True, "id": program.id})


# ---------------------------------------------------------------------------
# Delete program
# ---------------------------------------------------------------------------


@router.delete("/programs/{program_id}")
async def delete_program(program_id: str, request: Request, db: Session = Depends(get_db)):
    user = _require_user(request, db)
    if user is None:
        return JSONResponse({"ok": False, "error": "Not authenticated"}, status_code=401)

    program = db.query(Program).filter_by(id=program_id, user_id=user.id).first()
    if program is None:
        return JSONResponse({"ok": False, "error": "Program not found"}, status_code=404)

    db.delete(program)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Program detail
# ---------------------------------------------------------------------------


@router.get("/programs/{program_id}", response_class=HTMLResponse)
async def program_detail(program_id: str, request: Request, db: Session = Depends(get_db)):
    user = _require_user(request, db)
    if user is None:
        return RedirectResponse("/auth/login-forge", status_code=303)

    program = (
        db.query(Program)
        .options(joinedload(Program.program_sessions))
        .filter_by(id=program_id, user_id=user.id)
        .first()
    )
    if program is None:
        request.session["flash_error"] = "Program not found."
        return RedirectResponse("/my/programs", status_code=303)

    sessions_sorted = sorted(
        program.program_sessions, key=lambda s: (s.week_num, s.day_num)
    )
    goal_cfg = GOALS.get(program.goal, {})
    return render_template(
        "my_program_detail.html",
        request,
        db=db,
        program=program,
        program_sessions=sessions_sorted,
        goal_icon=goal_cfg.get("icon", "🏋️"),
        goal_label=goal_cfg.get("label", program.goal),
    )
