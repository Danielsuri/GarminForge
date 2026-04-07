"""
Program routes for multi-week training program management:
  GET    /my/programs           — list user's programs
  POST   /my/programs           — create a new program (stub; sessions added by generator in Initiative 2)
  DELETE /my/programs/{id}      — delete a program (cascades to program_sessions)
  GET    /my/programs/{id}      — program detail view
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from web.auth_utils import require_user
from web.db import get_db
from web.models import Program
from web.rendering import render_template
from web.workout_generator import GOALS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/my")

_require_user = require_user


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
# Create program (stub — no sessions generated until Initiative 2)
# ---------------------------------------------------------------------------


@router.post("/programs")
async def create_program(request: Request, db: Session = Depends(get_db)):
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
