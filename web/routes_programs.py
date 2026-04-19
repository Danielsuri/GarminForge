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
from datetime import date, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from sqlalchemy.orm import Session, joinedload

from web.auth_utils import require_user
from web.db import get_db
from web.models import NutritionPlan, Program, ProgramSession, User
from web.nutrition_generator import get_todays_meals, get_todays_reminder, last_sunday
from web.program_generator import generate_program
from web.rendering import render_template
from web.workout_generator import EQUIPMENT_OPTIONS, GOALS, _LOCAL_VIDEO_MAP

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/my")

_MUSCLE_MAP_SVG: str = ""
try:
    _MUSCLE_MAP_SVG = (Path(__file__).parent / "static" / "img" / "muscle_map.svg").read_text(
        encoding="utf-8"
    )
except Exception:
    pass

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
    profile_fitness_level: str = (user.fitness_level or "intermediate").lower()

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

    required = {
        "goal",
        "equipment",
        "duration_weeks",
        "weekly_workout_days",
        "duration_minutes",
        "periodization_type",
    }
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
        sessions_data.append(
            {
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
            }
        )

    return JSONResponse(
        {
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
        }
    )


# ---------------------------------------------------------------------------
# List programs
# ---------------------------------------------------------------------------


@router.get("/programs", response_class=HTMLResponse)
async def list_programs(request: Request, db: Session = Depends(get_db)):
    user = _require_user(request, db)
    if user is None:
        return RedirectResponse("/auth/login-forge", status_code=303)
    programs = (
        db.query(Program).filter_by(user_id=user.id).order_by(Program.created_at.desc()).all()
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
    today = date.today()
    weekly_workout_days = max((int(s["day_num"]) for s in sessions_data), default=1)
    day_spacing = max(1, 7 // weekly_workout_days)

    for s in sessions_data:
        week_num = int(s["week_num"])
        day_num = int(s["day_num"])
        day_offset = (week_num - 1) * 7 + (day_num - 1) * day_spacing
        program_session = ProgramSession(
            program_id=program.id,
            week_num=week_num,
            day_num=day_num,
            focus=str(s["focus"])[:100],
            garmin_payload_json=json.dumps(s["garmin_payload"]),
            exercises_json=json.dumps(s["exercises"]),
            scheduled_date=today + timedelta(days=day_offset),
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

    sessions_sorted = sorted(program.program_sessions, key=lambda s: (s.week_num, s.day_num))
    # Parse exercises per session for inline display
    sessions_exercises: dict[str, list[dict]] = {}
    for s in sessions_sorted:
        try:
            sessions_exercises[s.id] = json.loads(s.exercises_json)
        except Exception:
            sessions_exercises[s.id] = []

    goal_cfg = GOALS.get(program.goal, {})
    return render_template(
        "my_program_detail.html",
        request,
        db=db,
        program=program,
        program_sessions=sessions_sorted,
        sessions_exercises=sessions_exercises,
        goal_icon=goal_cfg.get("icon", "🏋️"),
        goal_label=goal_cfg.get("label", program.goal),
    )


# ---------------------------------------------------------------------------
# Session preview
# ---------------------------------------------------------------------------


@router.get("/programs/{program_id}/sessions/{session_id}", response_class=HTMLResponse)
async def session_preview(
    program_id: str, session_id: str, request: Request, db: Session = Depends(get_db)
):
    user = _require_user(request, db)
    if user is None:
        return RedirectResponse("/auth/login-forge", status_code=303)

    program = db.query(Program).filter_by(id=program_id, user_id=user.id).first()
    if program is None:
        request.session["flash_error"] = "Program not found."
        return RedirectResponse("/my/programs", status_code=303)

    session_obj = next((s for s in program.program_sessions if s.id == session_id), None)
    if session_obj is None:
        request.session["flash_error"] = "Session not found."
        return RedirectResponse(f"/my/programs/{program_id}", status_code=303)

    try:
        exercises = json.loads(session_obj.exercises_json)
    except Exception:
        exercises = []

    # Refresh video_url from the current media map so newly downloaded GIFs
    # are shown even for sessions generated before the GIFs existed.
    for ex in exercises:
        if isinstance(ex, dict):
            ex["video_url"] = _LOCAL_VIDEO_MAP.get(ex.get("name") or "")  # type: ignore[assignment]

    try:
        garmin_payload = json.loads(session_obj.garmin_payload_json)
    except Exception:
        garmin_payload = {}

    duration_minutes = int(garmin_payload.get("estimatedDurationInSecs", 2700)) // 60

    goal_cfg = GOALS.get(program.goal, {})

    # ── Nutrition card context ──
    from datetime import date as _date
    from typing import Any as _Any

    todays_meals: list[dict[str, _Any]] = []
    todays_reminder: str | None = None
    nutrition_status = "no_profile"

    if user.nutrition_profile_json:
        week_start = last_sunday(_date.today())
        nutrition_plan = (
            db.query(NutritionPlan).filter_by(user_id=user.id, week_start=week_start).first()
        )
        if nutrition_plan is None:
            nutrition_plan = NutritionPlan(
                user_id=user.id, week_start=week_start, status="generating"
            )
            db.add(nutrition_plan)
            db.commit()
            # NOTE: background_tasks is not available in this route — plan generation
            # will be triggered when the user visits /nutrition directly.
            nutrition_status = "generating"
        elif nutrition_plan.status == "ready":
            todays_meals = get_todays_meals(nutrition_plan)
            todays_reminder = get_todays_reminder(nutrition_plan)
            nutrition_status = "ready"
        elif nutrition_plan.status == "generating":
            nutrition_status = "generating"
        else:
            nutrition_status = "error"

    return render_template(
        "my_session_preview.html",
        request,
        db=db,
        program=program,
        session=session_obj,
        exercises=exercises,
        payload_json=session_obj.garmin_payload_json,
        goal_icon=goal_cfg.get("icon", "🏋️"),
        goal_label=goal_cfg.get("label", program.goal),
        duration_minutes=duration_minutes,
        muscle_map_svg=_MUSCLE_MAP_SVG,
        nutrition_status=nutrition_status,
        todays_meals=todays_meals,
        todays_reminder=todays_reminder,
    )


# ---------------------------------------------------------------------------
# Workout completion
# ---------------------------------------------------------------------------


def _mark_complete(
    session_obj: ProgramSession,
    *,
    actual_duration: int,
    post_to_strava: bool,
    user: User,
    db: Session,
) -> None:
    """Commit completion data and optionally post to Strava."""
    import os
    from datetime import datetime, timezone

    session_obj.completed_at = datetime.now(timezone.utc)
    session_obj.actual_duration_minutes = actual_duration

    if post_to_strava and user.strava_token_json and not session_obj.strava_activity_id:
        try:
            from garminforge.exceptions import StravaAuthError, StravaRateLimitError
            from web.strava_client import strava_client_from_user

            client_id = os.environ.get("STRAVA_CLIENT_ID", "")
            client_secret = os.environ.get("STRAVA_CLIENT_SECRET", "")
            strava = strava_client_from_user(user, client_id, client_secret)
            start_dt = session_obj.completed_at
            result = strava.create_activity(
                name=session_obj.focus,
                sport_type="WeightTraining",
                start_date_local=start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                elapsed_time=actual_duration * 60,
                description=(
                    f"GarminForge — Week {session_obj.week_num}, Day {session_obj.day_num}"
                ),
            )
            session_obj.strava_activity_id = str(result["id"])
            user.strava_token_json = json.dumps(strava.token.as_dict())
        except (StravaAuthError, StravaRateLimitError):
            pass  # Don't block completion on Strava errors

    db.commit()

    # Trigger recovery recalc and reschedule if fatigued
    if user.strava_activities_json:
        from web.strava_insights import recovery_score, reschedule_if_needed

        try:
            activities = json.loads(user.strava_activities_json)
        except Exception:
            activities = []
        if activities:
            recovery = recovery_score(activities)
            upcoming = (
                db.query(ProgramSession)
                .filter(
                    ProgramSession.program.has(user_id=user.id),  # type: ignore[attr-defined]
                    ProgramSession.completed_at.is_(None),
                )
                .all()
            )
            if upcoming:
                reschedule_if_needed(upcoming, recovery, db)


@router.get("/sessions/{session_id}/complete", response_class=HTMLResponse)
async def session_complete_get(
    session_id: str, request: Request, db: Session = Depends(get_db)
) -> Response:
    user = _require_user(request, db)
    if user is None:
        return RedirectResponse("/auth/login-forge", status_code=303)

    session_obj = db.query(ProgramSession).filter_by(id=session_id).first()
    if session_obj is None or session_obj.program.user_id != user.id:
        request.session["flash_error"] = "Session not found."
        return RedirectResponse("/my/programs", status_code=303)

    if session_obj.completed_at is not None:
        request.session["flash_error"] = "Session already completed."
        return RedirectResponse(f"/my/programs/{session_obj.program_id}", status_code=303)

    try:
        garmin_payload = json.loads(session_obj.garmin_payload_json)
    except Exception:
        garmin_payload = {}
    duration_minutes = int(garmin_payload.get("estimatedDurationInSecs", 2700)) // 60

    try:
        exercises = json.loads(session_obj.exercises_json)
    except Exception:
        exercises = []

    return render_template(
        "workout_complete.html",
        request,
        db=db,
        session=session_obj,
        duration_minutes=duration_minutes,
        exercises=exercises,
        strava_connected=bool(user.strava_token_json),
    )


@router.post("/sessions/{session_id}/complete", response_class=HTMLResponse)
async def session_complete_post(
    session_id: str,
    request: Request,
    actual_duration: int = Form(...),
    post_to_strava: bool = Form(default=False),
    db: Session = Depends(get_db),
) -> Response:
    user = _require_user(request, db)
    if user is None:
        return RedirectResponse("/auth/login-forge", status_code=303)

    session_obj = db.query(ProgramSession).filter_by(id=session_id).first()
    if session_obj is None or session_obj.program.user_id != user.id:
        request.session["flash_error"] = "Session not found."
        return RedirectResponse("/my/programs", status_code=303)

    if session_obj.completed_at is not None:
        request.session["flash_error"] = "Session already completed."
        return RedirectResponse(f"/my/programs/{session_obj.program_id}", status_code=303)

    if actual_duration < 1:
        request.session["flash_error"] = "Duration must be at least 1 minute."
        return RedirectResponse(f"/my/sessions/{session_id}/complete", status_code=303)

    _mark_complete(
        session_obj,
        actual_duration=actual_duration,
        post_to_strava=post_to_strava,
        user=user,
        db=db,
    )

    request.session["flash_success"] = "Workout logged!"
    return RedirectResponse("/my/profile", status_code=303)
