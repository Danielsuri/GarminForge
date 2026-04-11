"""
Multi-week periodized program generator.

Takes user inputs:
- goal, equipment, duration_weeks, weekly_workout_days, duration_minutes
- periodization_type: "linear" | "undulating" | "block"
- fitness_level:      "beginner" | "intermediate" | "advanced"

Produces:
- A ``ProgramPlan`` containing one ``SessionPlan`` per training day across all
  weeks, each with a Garmin-ready payload and rich exercise metadata.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, NamedTuple

from sqlalchemy.orm import Session

from web.models import Program, ProgramSession, User
from web.workout_generator import (
    GOALS,
    ExerciseInfo,
    WorkoutPlan,
    _generate_session,  # type: ignore[attr-defined]
)


# ---------------------------------------------------------------------------
# Phase parameters
# ---------------------------------------------------------------------------

class PhaseParams(NamedTuple):
    sets: int
    reps_low: int        # lower bound of rep range (for display)
    reps_high: int       # upper bound; passed to _generate_session as override_reps
    rest_seconds: int


# Concrete phase tables for linear / block periodization
# keyed by (duration_weeks, week_num) → phase name
_LINEAR_PHASES: dict[int, list[str]] = {
    4: ["acc", "acc", "int", "peak"],
    6: ["acc", "acc", "deload", "int", "int", "peak"],
    8: ["acc", "acc", "acc", "deload", "int", "int", "int", "peak"],
}

_PHASE_PARAMS: dict[str, PhaseParams] = {
    "acc":    PhaseParams(sets=3, reps_low=12, reps_high=15, rest_seconds=60),
    "deload": PhaseParams(sets=2, reps_low=12, reps_high=15, rest_seconds=60),
    "int":    PhaseParams(sets=4, reps_low=6,  reps_high=10, rest_seconds=90),
    "peak":   PhaseParams(sets=5, reps_low=3,  reps_high=5,  rest_seconds=120),
}

# Undulating: cycles through day_slot mod 3
_UNDULATING_SLOTS: list[PhaseParams] = [
    PhaseParams(sets=5, reps_low=3,  reps_high=5,  rest_seconds=120),  # strength
    PhaseParams(sets=4, reps_low=8,  reps_high=12, rest_seconds=90),   # hypertrophy
    PhaseParams(sets=3, reps_low=12, reps_high=15, rest_seconds=60),   # endurance
]


def _phase_params(
    week_num: int,
    duration_weeks: int,
    periodization_type: str,
    day_slot: int,
) -> PhaseParams:
    """Return phase parameters for a given week / day slot.

    Parameters
    ----------
    week_num:
        1-based week number.
    duration_weeks:
        Total program length (4, 6, or 8 weeks).
    periodization_type:
        "linear" | "undulating" | "block"
    day_slot:
        0-based index of the training day within the week's split pattern.
        Used only for undulating periodization.
    """
    if periodization_type == "undulating":
        return _UNDULATING_SLOTS[day_slot % 3]

    if periodization_type == "linear":
        # Look up phase table; fall back to 8-week for durations > 8
        phases = _LINEAR_PHASES.get(duration_weeks, _LINEAR_PHASES[8])
        phase_key = phases[min(week_num - 1, len(phases) - 1)]
        return _PHASE_PARAMS[phase_key]

    # block
    n = duration_weeks
    block_size = max(1, n // 3)
    has_deload = n >= 6

    acc_end = block_size
    deload_week = acc_end + 1 if has_deload else None
    int_start = (deload_week + 1) if deload_week else (acc_end + 1)
    int_end = int_start + block_size - 1

    if week_num <= acc_end:
        return _PHASE_PARAMS["acc"]
    if deload_week and week_num == deload_week:
        return _PHASE_PARAMS["deload"]
    if week_num <= int_end:
        return _PHASE_PARAMS["int"]
    return _PHASE_PARAMS["peak"]


# ---------------------------------------------------------------------------
# Split patterns
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SplitDay:
    key: str               # internal identifier
    label: str             # full focus label, e.g. "Upper Body — Push"
    short: str             # abbreviated, used in workout_name, e.g. "Push"
    muscle_groups: list[str]


_SPLITS: dict[int, list[SplitDay]] = {
    2: [
        SplitDay("full_body_a", "Full Body A", "Full Body A", ["push", "pull", "squat", "core"]),
        SplitDay("full_body_b", "Full Body B", "Full Body B", ["push", "pull", "hinge", "core"]),
    ],
    3: [
        SplitDay("push", "Upper Body — Push", "Push", ["push", "shoulders", "arms_tri"]),
        SplitDay("pull", "Upper Body — Pull", "Pull", ["pull", "arms_bi"]),
        SplitDay("legs", "Lower Body",         "Legs", ["squat", "hinge", "lunge", "calves"]),
    ],
    4: [
        SplitDay("upper_push", "Upper Body — Horizontal Push", "Upper Push", ["push", "shoulders"]),
        SplitDay("lower_a",    "Lower Body",                   "Lower",      ["squat", "hinge", "lunge"]),
        SplitDay("upper_pull", "Upper Body — Vertical Pull",   "Upper Pull", ["pull", "arms_bi"]),
        SplitDay("lower_b",    "Lower Body",                   "Lower",      ["squat", "hinge", "calves"]),
    ],
    5: [
        SplitDay("push",  "Upper Body — Push", "Push",  ["push", "shoulders", "arms_tri"]),
        SplitDay("pull",  "Upper Body — Pull", "Pull",  ["pull", "arms_bi"]),
        SplitDay("legs",  "Lower Body",        "Legs",  ["squat", "hinge", "lunge", "calves"]),
        SplitDay("upper", "Upper Body",        "Upper", ["push", "pull", "shoulders"]),
        SplitDay("lower", "Lower Body",        "Lower", ["squat", "hinge"]),
    ],
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SessionPlan:
    """One training session within a multi-week program."""
    week_num: int
    day_num: int
    focus: str               # "Upper Body — Push"
    workout_name: str        # "Week 2 Day 1 · Push — 45 min"
    phase: str               # "acc" | "deload" | "int" | "peak" | "strength" | etc.
    sets: int
    reps_low: int
    reps_high: int
    rest_seconds: int
    exercises: list[ExerciseInfo]
    garmin_payload: dict[str, Any]


@dataclass
class ProgramPlan:
    """A full multi-week periodized training program."""
    name: str
    goal: str
    goal_label: str
    goal_icon: str
    periodization_type: str
    duration_weeks: int
    weekly_workout_days: int
    duration_minutes: int
    equipment: list[str]
    sessions: list[SessionPlan]   # length = duration_weeks × weekly_workout_days


# ---------------------------------------------------------------------------
# Seed helper
# ---------------------------------------------------------------------------

def _session_seed(base_seed: int | None, week: int, day_idx: int) -> int | None:
    """Deterministic per-session seed so preview is reproducible."""
    if base_seed is None:
        return None
    return base_seed ^ (week * 1000 + day_idx)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_program(
    goal: str,
    equipment: list[str],
    duration_weeks: int,
    weekly_workout_days: int,
    duration_minutes: int,
    periodization_type: str = "linear",
    fitness_level: str = "intermediate",  # reserved for future difficulty scaling
    seed: int | None = None,
) -> ProgramPlan:
    """Generate a full multi-week periodized training program.

    Parameters
    ----------
    goal:
        One of the ``GOALS`` keys (e.g. ``"build_muscle"``).
    equipment:
        List of equipment tags from ``EQUIPMENT_OPTIONS``.
    duration_weeks:
        Program length in weeks. Typically 4, 6, or 8.
    weekly_workout_days:
        Number of training days per week (2–5).
    duration_minutes:
        Target session duration in minutes (applies to every session).
    periodization_type:
        ``"linear"``, ``"undulating"``, or ``"block"``.
    fitness_level:
        ``"beginner"``, ``"intermediate"``, or ``"advanced"``.
        Reserved for future difficulty scaling; not used in generation yet.
    seed:
        Optional base seed for reproducible generation.
    """
    if goal not in GOALS:
        raise ValueError(f"Unknown goal {goal!r}. Choose from: {list(GOALS)}")
    if periodization_type not in ("linear", "undulating", "block"):
        raise ValueError(
            f"Unknown periodization_type {periodization_type!r}. "
            "Choose from: linear, undulating, block"
        )
    if weekly_workout_days not in _SPLITS:
        raise ValueError(
            f"weekly_workout_days must be one of {list(_SPLITS)}; got {weekly_workout_days}"
        )
    if duration_weeks < 1:
        raise ValueError("duration_weeks must be at least 1")

    goal_cfg = GOALS[goal]
    split = _SPLITS[weekly_workout_days]

    # For linear/block, snap duration_weeks to the nearest supported table
    # (4, 6, 8).  Undulating works for any duration.
    if periodization_type in ("linear",) and duration_weeks not in _LINEAR_PHASES:
        # find nearest supported length
        supported = sorted(_LINEAR_PHASES.keys())
        duration_weeks_clamped = min(supported, key=lambda x: abs(x - duration_weeks))
    else:
        duration_weeks_clamped = duration_weeks

    sessions: list[SessionPlan] = []

    for week in range(1, duration_weeks + 1):
        for day_idx, split_day in enumerate(split):
            phase = _phase_params(week, duration_weeks_clamped, periodization_type, day_idx)
            name = f"Week {week} Day {day_idx + 1} · {split_day.short} — {duration_minutes} min"

            plan: WorkoutPlan = _generate_session(
                equipment=equipment if equipment else ["bodyweight"],
                goal=goal,
                duration_minutes=duration_minutes,
                muscle_groups=split_day.muscle_groups,
                override_sets=phase.sets,
                override_reps=phase.reps_high,
                override_rest=phase.rest_seconds,
                workout_name=name,
                seed=_session_seed(seed, week, day_idx),
            )

            # Determine a human-readable phase label
            if periodization_type == "undulating":
                phase_labels = ["Strength", "Hypertrophy", "Endurance"]
                phase_label = phase_labels[day_idx % 3]
            else:
                phase_label = {
                    "acc": "Accumulation",
                    "deload": "Deload",
                    "int": "Intensification",
                    "peak": "Peak",
                }.get(
                    (_LINEAR_PHASES.get(duration_weeks_clamped, _LINEAR_PHASES[8])[week - 1]
                     if periodization_type == "linear"
                     else _block_phase_key(week, duration_weeks_clamped)),
                    "Training",
                )

            sessions.append(SessionPlan(
                week_num=week,
                day_num=day_idx + 1,
                focus=split_day.label,
                workout_name=name,
                phase=phase_label,
                sets=phase.sets,
                reps_low=phase.reps_low,
                reps_high=phase.reps_high,
                rest_seconds=phase.rest_seconds,
                exercises=plan.exercises,
                garmin_payload=plan.garmin_payload,
            ))

    program_name = f"{duration_weeks}-Week {goal_cfg['label']}"

    return ProgramPlan(
        name=program_name,
        goal=goal,
        goal_label=goal_cfg["label"],
        goal_icon=goal_cfg["icon"],
        periodization_type=periodization_type,
        duration_weeks=duration_weeks,
        weekly_workout_days=weekly_workout_days,
        duration_minutes=duration_minutes,
        equipment=equipment,
        sessions=sessions,
    )


def _block_phase_key(week_num: int, duration_weeks: int) -> str:
    """Return the phase key for block periodization at the given week."""
    n = duration_weeks
    block_size = max(1, n // 3)
    has_deload = n >= 6
    acc_end = block_size
    deload_week = acc_end + 1 if has_deload else None
    int_start = (deload_week + 1) if deload_week else (acc_end + 1)
    int_end = int_start + block_size - 1
    if week_num <= acc_end:
        return "acc"
    if deload_week and week_num == deload_week:
        return "deload"
    if week_num <= int_end:
        return "int"
    return "peak"


# ---------------------------------------------------------------------------
# Auto-generate program from user questionnaire data
# ---------------------------------------------------------------------------

_GOAL_PERIODIZATION: dict[str, str] = {
    "burn_fat":       "linear",
    "lose_weight":    "linear",
    "build_muscle":   "block",
    "build_strength": "block",
    "general_fitness": "undulating",
    "endurance":      "undulating",
}

_DAY_TO_WEEKDAY: dict[str, int] = {
    "Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3,
    "Fri": 4, "Sat": 5, "Sun": 6,
}


def auto_generate_program(user: User, db: Session) -> Program:
    """Create and persist an 8-week program derived from the user's questionnaire answers.

    Parameters
    ----------
    user:
        User instance with questionnaire fields populated.
    db:
        SQLAlchemy Session.

    Returns the created (and committed) Program instance.
    """
    # Idempotent: don't create a second active program
    existing = db.query(Program).filter_by(user_id=user.id, status="active").first()
    if existing is not None:
        return existing

    # Resolve goal
    goals: list[str] = json.loads(user.fitness_goals_json or "[]")
    goal = goals[0] if goals else "general_fitness"
    if goal not in GOALS:
        goal = "general_fitness"

    periodization = _GOAL_PERIODIZATION.get(goal, "undulating")

    # Resolve equipment
    equipment: list[str] = json.loads(user.preferred_equipment_json or '["bodyweight"]')
    if not equipment:
        equipment = ["bodyweight"]

    # Resolve training days
    raw_days: list[str] = json.loads(user.preferred_days_json or "[]")
    # Filter to valid day names, sort by weekday, then clamp to supported split range (2-5)
    valid_days = sorted(
        [d for d in raw_days if d in _DAY_TO_WEEKDAY],
        key=lambda d: _DAY_TO_WEEKDAY[d],
    )
    n_days = max(2, min(5, len(valid_days))) if valid_days else 3
    sorted_days = valid_days[:n_days]

    fitness_level = (user.fitness_level or "intermediate").lower()
    duration_weeks = 8
    duration_minutes = 45

    plan = generate_program(
        goal=goal,
        equipment=equipment,
        duration_weeks=duration_weeks,
        weekly_workout_days=n_days,
        duration_minutes=duration_minutes,
        periodization_type=periodization,
        fitness_level=fitness_level,
    )

    program = Program(
        user_id=user.id,
        name=plan.name,
        goal=goal,
        periodization_type=periodization,
        duration_weeks=duration_weeks,
        equipment_json=json.dumps(equipment),
        status="active",
    )
    db.add(program)
    db.flush()  # populate program.id

    today = date.today()

    # Build a list of calendar dates for each session.
    # If the user chose specific days, schedule on those actual weekdays.
    # Otherwise fall back to even spacing.
    session_dates: list[date] = []
    if sorted_days:
        weekday_nums = [_DAY_TO_WEEKDAY[d] for d in sorted_days]
        # Start from next Monday so the user has time to see their plan
        days_to_monday = today.weekday()
        this_monday = today - timedelta(days=days_to_monday)
        next_monday = this_monday + timedelta(weeks=1)
        for week in range(duration_weeks):
            week_monday = next_monday + timedelta(weeks=week)
            for wd in weekday_nums:
                session_dates.append(week_monday + timedelta(days=wd))
    else:
        day_spacing = max(1, 7 // n_days)
        for i in range(duration_weeks * n_days):
            session_dates.append(today + timedelta(days=i * day_spacing))

    for idx, session_plan in enumerate(plan.sessions):
        scheduled = session_dates[idx] if idx < len(session_dates) else None
        ps = ProgramSession(
            program_id=program.id,
            week_num=session_plan.week_num,
            day_num=session_plan.day_num,
            focus=session_plan.focus,
            garmin_payload_json=json.dumps(session_plan.garmin_payload),
            exercises_json=json.dumps(
                [
                    {
                        "category": e.category,
                        "name": e.name,
                        "label": e.label,
                        "sets": e.sets,
                        "reps": e.reps,
                        "duration_sec": e.duration_sec,
                        "rest_seconds": e.rest_seconds,
                        "muscle_group": e.muscle_group,
                        "primary_muscles": e.primary_muscles,
                        "secondary_muscles": e.secondary_muscles,
                        "video_url": e.video_url,
                    }
                    for e in session_plan.exercises
                ]
            ),
            scheduled_date=scheduled,
        )
        db.add(ps)

    # Update user.weekly_workout_days for backward compat
    user.weekly_workout_days = n_days  # type: ignore[assignment]
    db.commit()
    db.refresh(program)
    return program
