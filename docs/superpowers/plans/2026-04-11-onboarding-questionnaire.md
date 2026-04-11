# Onboarding Questionnaire & Dashboard Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the questionnaire the first experience for new users (before account creation), auto-generate a program on sign-up, and upgrade the session preview page to serve as the home screen.

**Architecture:** A new `/onboarding` route (in `web/routes_onboarding.py`) serves the shared questionnaire for guests and logged-in users. Guest answers live in `request.session["pending_q"]` until a new `POST /register` route creates the account, consumes the answers, and auto-generates a program. The `GET /` handler is updated to always redirect authenticated users to their active program session — the old generator-dashboard fallback is removed.

**Tech Stack:** FastAPI, Jinja2, SQLAlchemy (SQLite), Alembic, Python 3.11+, Bootstrap 5 + custom CSS (existing Koda design system).

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `web/migrations/versions/0004_add_onboarding_fields.py` | Create | Alembic migration for 4 new User columns |
| `web/models.py` | Modify | Add `age_range`, `preferred_days_json`, `height_cm`, `weight_kg` to `User` |
| `web/program_generator.py` | Modify | Add `auto_generate_program(user, db)` function |
| `web/routes_onboarding.py` | Create | `GET/POST /onboarding` — shared questionnaire route |
| `web/routes_auth.py` | Modify | Add `POST /register`; update OAuth callbacks to redirect to `/onboarding` |
| `web/routes_my.py` | Modify | Redirect `GET/POST /my/questionnaire` → `/onboarding`; remove skip route |
| `web/app.py` | Modify | Update `GET /` routing; register `routes_onboarding` router |
| `web/templates/questionnaire.html` | Modify | Reorder to 9 steps; goal image cards; age range cards; day-picker; height/weight; sign-up card |
| `web/templates/my_session_preview.html` | Modify | Add exercise-row thumbnails + nutrition coming-soon card |
| `tests/test_onboarding.py` | Create | Tests for `auto_generate_program`, onboarding route, and `/` redirect logic |

---

## Task 1: DB Migration — Add Onboarding Columns

**Files:**
- Create: `web/migrations/versions/0004_add_onboarding_fields.py`

- [ ] **Step 1: Write the migration file**

```python
# web/migrations/versions/0004_add_onboarding_fields.py
"""add age_range, preferred_days_json, height_cm, weight_kg to users

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-11
"""
from __future__ import annotations
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("age_range", sa.String(10), nullable=True))
    op.add_column("users", sa.Column("preferred_days_json", sa.Text, nullable=True))
    op.add_column("users", sa.Column("height_cm", sa.Float, nullable=True))
    op.add_column("users", sa.Column("weight_kg", sa.Float, nullable=True))


def downgrade() -> None:
    op.drop_column("users", "weight_kg")
    op.drop_column("users", "height_cm")
    op.drop_column("users", "preferred_days_json")
    op.drop_column("users", "age_range")
```

- [ ] **Step 2: Run the migration**

```bash
alembic upgrade head
```

Expected output: `Running upgrade 0003 -> 0004, add age_range, preferred_days_json, height_cm, weight_kg to users`

- [ ] **Step 3: Verify columns exist**

```bash
python -c "
import sqlite3, os
db_path = os.path.expanduser('~/.garminforge.db')
conn = sqlite3.connect(db_path)
cols = [r[1] for r in conn.execute('PRAGMA table_info(users)').fetchall()]
print(cols)
assert 'age_range' in cols
assert 'preferred_days_json' in cols
assert 'height_cm' in cols
assert 'weight_kg' in cols
print('OK')
"
```

Expected: prints column list with the 4 new names, then `OK`.

- [ ] **Step 4: Commit**

```bash
git add web/migrations/versions/0004_add_onboarding_fields.py
git commit -m "feat(db): migration 0004 — add age_range, preferred_days_json, height_cm, weight_kg"
```

---

## Task 2: Update User Model

**Files:**
- Modify: `web/models.py:32-42`

- [ ] **Step 1: Write failing test**

```python
# tests/test_onboarding.py
from web.models import User

def test_user_has_new_fields():
    u = User(email="t@test.com")
    assert hasattr(u, "age_range")
    assert hasattr(u, "preferred_days_json")
    assert hasattr(u, "height_cm")
    assert hasattr(u, "weight_kg")
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
pytest tests/test_onboarding.py::test_user_has_new_fields -v
```

Expected: `AttributeError` or `FAILED`.

- [ ] **Step 3: Add fields to User model**

In `web/models.py`, replace the onboarding questionnaire block (lines 32–42):

```python
    # Onboarding questionnaire
    questionnaire_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    age_range: Mapped[str | None] = mapped_column(String(10), nullable=True)      # "18-29" | "30-39" | "40-49" | "50+"
    preferred_days_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list e.g. '["Mon","Wed","Fri"]'
    height_cm: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    diet_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    health_conditions_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_equipment_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    fitness_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fitness_goals_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    weekly_workout_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

Also add `Float` to the sqlalchemy imports at line 9:

```python
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
pytest tests/test_onboarding.py::test_user_has_new_fields -v
```

Expected: `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add web/models.py tests/test_onboarding.py
git commit -m "feat(model): add age_range, preferred_days_json, height_cm, weight_kg to User"
```

---

## Task 3: `auto_generate_program()` in program_generator.py

**Files:**
- Modify: `web/program_generator.py` (append at end of file)

- [ ] **Step 1: Write failing test**

Add to `tests/test_onboarding.py`:

```python
import json
from unittest.mock import MagicMock
from web.program_generator import auto_generate_program
from web.models import User, Program, ProgramSession


def _make_user(**kwargs):
    defaults = dict(
        id="test-user-1",
        email="t@test.com",
        fitness_goals_json=json.dumps(["build_muscle"]),
        preferred_equipment_json=json.dumps(["barbell", "dumbbell"]),
        preferred_days_json=json.dumps(["Mon", "Wed", "Fri"]),
        fitness_level="Intermediate",
        questionnaire_completed=True,
    )
    defaults.update(kwargs)
    u = User(**{k: v for k, v in defaults.items()})
    return u


def test_auto_generate_program_creates_program_and_sessions():
    user = _make_user()
    db = MagicMock()
    db.query.return_value.filter_by.return_value.first.return_value = None  # no existing active program
    added = []
    db.add.side_effect = added.append
    db.flush.return_value = None
    db.commit.return_value = None
    db.refresh.return_value = None

    program = auto_generate_program(user, db)

    assert isinstance(program, Program)
    assert program.goal == "build_muscle"
    assert program.periodization_type == "block"
    assert program.status == "active"
    # 3 days/week × 8 weeks = 24 sessions
    session_objects = [x for x in added if isinstance(x, ProgramSession)]
    assert len(session_objects) == 24


def test_auto_generate_program_maps_periodization():
    for goal, expected_periodization in [
        ("burn_fat", "linear"),
        ("lose_weight", "linear"),
        ("build_muscle", "block"),
        ("build_strength", "block"),
        ("general_fitness", "undulating"),
        ("endurance", "undulating"),
    ]:
        user = _make_user(fitness_goals_json=json.dumps([goal]))
        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.return_value = None
        db.add.side_effect = lambda x: None
        db.flush.return_value = None
        db.commit.return_value = None
        db.refresh.return_value = None
        program = auto_generate_program(user, db)
        assert program.periodization_type == expected_periodization, f"goal={goal}"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_onboarding.py::test_auto_generate_program_creates_program_and_sessions tests/test_onboarding.py::test_auto_generate_program_maps_periodization -v
```

Expected: `ImportError` or `FAILED`.

- [ ] **Step 3: Implement `auto_generate_program()`**

Append to the end of `web/program_generator.py`:

```python
# ---------------------------------------------------------------------------
# Auto-generate program from user questionnaire data
# ---------------------------------------------------------------------------

import json as _json
from datetime import date as _date, timedelta as _timedelta

from web.models import Program as _Program, ProgramSession as _ProgramSession

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


def _next_weekday(from_date: _date, weekday: int) -> _date:
    """Return the next occurrence of `weekday` (0=Mon) on or after `from_date`."""
    days_ahead = weekday - from_date.weekday()
    if days_ahead < 0:
        days_ahead += 7
    return from_date + _timedelta(days=days_ahead)


def auto_generate_program(user: "User", db) -> _Program:  # type: ignore[name-defined]
    """Create and persist an 8-week program derived from the user's questionnaire answers.

    Parameters
    ----------
    user:
        User instance with questionnaire fields populated.
    db:
        SQLAlchemy Session.

    Returns the created (and committed) Program instance.
    """
    # Resolve goal
    goals: list[str] = _json.loads(user.fitness_goals_json or "[]")
    goal = goals[0] if goals else "general_fitness"
    if goal not in GOALS:
        goal = "general_fitness"

    periodization = _GOAL_PERIODIZATION.get(goal, "undulating")

    # Resolve equipment
    equipment: list[str] = _json.loads(user.preferred_equipment_json or '["bodyweight"]')
    if not equipment:
        equipment = ["bodyweight"]

    # Resolve training days
    raw_days: list[str] = _json.loads(user.preferred_days_json or "[]")
    # Clamp to supported split sizes (2–5); prefer the actual count
    n_days = max(2, min(5, len(raw_days))) if raw_days else 3
    # Keep only the first n_days entries (sorted by calendar order)
    sorted_days = sorted(raw_days[:n_days], key=lambda d: _DAY_TO_WEEKDAY.get(d, 9))

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

    goal_cfg = GOALS[goal]
    program = _Program(
        user_id=user.id,
        name=plan.name,
        goal=goal,
        periodization_type=periodization,
        duration_weeks=duration_weeks,
        equipment_json=_json.dumps(equipment),
        status="active",
    )
    db.add(program)
    db.flush()  # populate program.id

    today = _date.today()

    # Build a list of calendar dates for each session.
    # If the user chose specific days, schedule on those actual weekdays.
    # Otherwise fall back to even spacing.
    session_dates: list[_date] = []
    if sorted_days:
        weekday_nums = [_DAY_TO_WEEKDAY[d] for d in sorted_days if d in _DAY_TO_WEEKDAY]
        if not weekday_nums:
            weekday_nums = list(range(n_days))
        # Find the first occurrence of each preferred day starting from today (or tomorrow)
        start = today
        week_starts: list[_date] = []
        # Find Monday of the current week, then jump to "next" week for clean start
        days_to_monday = start.weekday()
        this_monday = start - _timedelta(days=days_to_monday)
        # Start from next Monday so the user has time to see their plan
        next_monday = this_monday + _timedelta(weeks=1)
        for week in range(duration_weeks):
            week_monday = next_monday + _timedelta(weeks=week)
            for wd in weekday_nums:
                session_dates.append(week_monday + _timedelta(days=wd))
    else:
        day_spacing = max(1, 7 // n_days)
        for i in range(duration_weeks * n_days):
            session_dates.append(today + _timedelta(days=i * day_spacing))

    for idx, session_plan in enumerate(plan.sessions):
        scheduled = session_dates[idx] if idx < len(session_dates) else None
        ps = _ProgramSession(
            program_id=program.id,
            week_num=session_plan.week_num,
            day_num=session_plan.day_num,
            focus=session_plan.focus,
            garmin_payload_json=_json.dumps(session_plan.garmin_payload),
            exercises_json=_json.dumps(
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
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_onboarding.py::test_auto_generate_program_creates_program_and_sessions tests/test_onboarding.py::test_auto_generate_program_maps_periodization -v
```

Expected: both `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add web/program_generator.py tests/test_onboarding.py
git commit -m "feat(program): auto_generate_program() from questionnaire answers"
```

---

## Task 4: New `/onboarding` Route

**Files:**
- Create: `web/routes_onboarding.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_onboarding.py`:

```python
from fastapi.testclient import TestClient
from web.app import app

client = TestClient(app, raise_server_exceptions=False)


def test_onboarding_get_accessible_without_login():
    resp = client.get("/onboarding", follow_redirects=False)
    assert resp.status_code == 200


def test_root_redirects_unauthenticated_to_onboarding():
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert resp.headers["location"] in ("/onboarding", "http://testserver/onboarding")
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_onboarding.py::test_onboarding_get_accessible_without_login tests/test_onboarding.py::test_root_redirects_unauthenticated_to_onboarding -v
```

Expected: `FAILED` (404 for /onboarding, wrong redirect for /).

- [ ] **Step 3: Create `web/routes_onboarding.py`**

```python
"""
Shared onboarding questionnaire route:
  GET  /onboarding — render questionnaire (guest or logged-in)
  POST /onboarding — save answers (guest → session; logged-in → DB + auto-program)
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from web.auth_utils import get_current_user
from web.db import get_db
from web.models import Program
from web.program_generator import auto_generate_program
from web.rendering import render_template
from web.workout_generator import EQUIPMENT_OPTIONS, GOALS

logger = logging.getLogger(__name__)
router = APIRouter()

# Goal options aligned with workout_generator.GOALS keys (used for image cards)
GOAL_OPTIONS = [
    {"value": "burn_fat",        "label": "Burn Fat",           "image": "/static/img/burn-fat.png"},
    {"value": "lose_weight",     "label": "Lose Weight",        "image": "/static/img/lose-weight.png"},
    {"value": "build_muscle",    "label": "Build Muscle",       "image": "/static/img/build-mucsle.png"},
    {"value": "build_strength",  "label": "Build Strength",     "image": "/static/img/build-strength.png"},
    {"value": "general_fitness", "label": "General Fitness",    "image": "/static/img/general-fitness.png"},
    {"value": "endurance",       "label": "Muscular Endurance", "image": "/static/img/muscular-endurance.png"},
]

AGE_RANGES = ["18-29", "30-39", "40-49", "50+"]

DIET_OPTIONS = [
    {"value": "general",       "label": "General"},
    {"value": "vegetarian",    "label": "Vegetarian"},
    {"value": "vegan",         "label": "Vegan"},
    {"value": "keto",          "label": "Keto"},
    {"value": "paleo",         "label": "Paleo"},
    {"value": "mediterranean", "label": "Mediterranean"},
    {"value": "gluten_free",   "label": "Gluten-Free"},
    {"value": "high_protein",  "label": "High Protein"},
]

HEALTH_OPTIONS = [
    {"value": "heart_condition",    "label": "Heart Condition"},
    {"value": "diabetes",           "label": "Diabetes"},
    {"value": "high_blood_pressure","label": "High Blood Pressure"},
    {"value": "joint_problems",     "label": "Joint Problems"},
    {"value": "back_pain",          "label": "Back Pain"},
    {"value": "asthma",             "label": "Asthma"},
]

FITNESS_LEVELS = [
    {"value": "Beginner",     "label": "Beginner"},
    {"value": "Intermediate", "label": "Intermediate"},
    {"value": "Advanced",     "label": "Advanced"},
]

DAYS_OF_WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _decode(val: str | None) -> list:
    if not val:
        return []
    try:
        return json.loads(val)
    except Exception:
        return []


@router.get("/onboarding", response_class=HTMLResponse)
async def onboarding_get(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    pending = request.session.get("pending_q", {})
    return render_template(
        "questionnaire.html",
        request,
        db=db,
        goal_options=GOAL_OPTIONS,
        age_ranges=AGE_RANGES,
        fitness_levels=FITNESS_LEVELS,
        diet_options=DIET_OPTIONS,
        health_options=HEALTH_OPTIONS,
        equipment_options=EQUIPMENT_OPTIONS,
        days_of_week=DAYS_OF_WEEK,
        is_guest=(user is None),
        is_retake=(user is not None and user.questionnaire_completed),
        # Pre-fill from DB (retake) or session (guest returning to page)
        existing_goals=_decode(user.fitness_goals_json if user else pending.get("fitness_goals_json")),
        existing_age_range=(user.age_range if user else pending.get("age_range", "")),
        existing_fitness_level=(user.fitness_level if user else pending.get("fitness_level", "")),
        existing_days=_decode(user.preferred_days_json if user else pending.get("preferred_days_json")),
        existing_equipment=_decode(user.preferred_equipment_json if user else pending.get("preferred_equipment_json")),
        existing_height_cm=(user.height_cm if user else pending.get("height_cm")),
        existing_weight_kg=(user.weight_kg if user else pending.get("weight_kg")),
        existing_diet=_decode(user.diet_json if user else pending.get("diet_json")),
        existing_health=_decode(user.health_conditions_json if user else pending.get("health_conditions_json")),
    )


@router.post("/onboarding")
async def onboarding_post(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    user = get_current_user(request, db)

    answers: dict = {
        "fitness_goals_json":     json.dumps(form.getlist("fitness_goals")),
        "age_range":              form.get("age_range", ""),
        "fitness_level":          form.get("fitness_level", ""),
        "preferred_days_json":    json.dumps(form.getlist("preferred_days")),
        "preferred_equipment_json": json.dumps(form.getlist("equipment")),
        "height_cm":              _parse_float(form.get("height_cm")),
        "weight_kg":              _parse_float(form.get("weight_kg")),
        "diet_json":              json.dumps(form.getlist("diet")),
        "health_conditions_json": json.dumps(form.getlist("health_conditions")),
    }

    if user is None:
        # Guest: stash answers in session, proceed to sign-up card
        request.session["pending_q"] = {k: v for k, v in answers.items() if v is not None}
        return RedirectResponse("/register", status_code=303)

    # Logged-in: persist to DB
    _apply_answers(user, answers)
    user.questionnaire_completed = True  # type: ignore[assignment]

    # Auto-generate program if user has no active program
    active = db.query(Program).filter_by(user_id=user.id, status="active").first()
    if active is None:
        auto_generate_program(user, db)
    else:
        db.commit()

    request.session["flash_success"] = "Profile updated."
    return RedirectResponse("/", status_code=303)


def _parse_float(val: str | None) -> float | None:
    if not val:
        return None
    try:
        return float(val)
    except ValueError:
        return None


def _apply_answers(user, answers: dict) -> None:
    """Write parsed questionnaire answers onto the user ORM object."""
    user.fitness_goals_json = answers.get("fitness_goals_json")           # type: ignore[assignment]
    user.age_range = answers.get("age_range") or None                      # type: ignore[assignment]
    user.fitness_level = answers.get("fitness_level") or None              # type: ignore[assignment]
    user.preferred_days_json = answers.get("preferred_days_json")          # type: ignore[assignment]
    user.preferred_equipment_json = answers.get("preferred_equipment_json")# type: ignore[assignment]
    user.height_cm = answers.get("height_cm")                              # type: ignore[assignment]
    user.weight_kg = answers.get("weight_kg")                              # type: ignore[assignment]
    user.diet_json = answers.get("diet_json")                              # type: ignore[assignment]
    user.health_conditions_json = answers.get("health_conditions_json")    # type: ignore[assignment]
```

- [ ] **Step 4: Register the router in `web/app.py`**

Find the section where other routers are imported and included (look for `app.include_router`). Add:

```python
from web.routes_onboarding import router as onboarding_router
# ...
app.include_router(onboarding_router)
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_onboarding.py::test_onboarding_get_accessible_without_login tests/test_onboarding.py::test_root_redirects_unauthenticated_to_onboarding -v
```

Expected: both `PASSED`.

- [ ] **Step 6: Commit**

```bash
git add web/routes_onboarding.py web/app.py tests/test_onboarding.py
git commit -m "feat(routes): add /onboarding route (guest + logged-in questionnaire)"
```

---

## Task 5: Update `GET /` Routing in `app.py`

**Files:**
- Modify: `web/app.py:228-291`

- [ ] **Step 1: Write failing test**

Add to `tests/test_onboarding.py`:

```python
def test_root_authenticated_no_questionnaire_redirects_to_onboarding(monkeypatch):
    """Authenticated user with questionnaire_completed=False → /onboarding."""
    from web import app as app_module
    from web.auth_utils import get_current_user

    fake_user = MagicMock()
    fake_user.questionnaire_completed = False
    monkeypatch.setattr(app_module, "get_current_user", lambda req, db: fake_user)

    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert "/onboarding" in resp.headers["location"]
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
pytest tests/test_onboarding.py::test_root_authenticated_no_questionnaire_redirects_to_onboarding -v
```

Expected: `FAILED`.

- [ ] **Step 3: Rewrite the `index` route in `web/app.py`**

Replace the body of `async def index(...)` (starting at line 228):

```python
@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    db: Session = Depends(get_db),
):
    forge_user = get_current_user(request, db)

    # Unauthenticated → onboarding
    if forge_user is None:
        return RedirectResponse("/onboarding", status_code=303)

    # Authenticated but questionnaire not done → onboarding
    if not forge_user.questionnaire_completed:
        return RedirectResponse("/onboarding", status_code=303)

    # Find active program
    active_program = (
        db.query(Program)
        .filter_by(user_id=forge_user.id, status="active")
        .first()
    )

    # No active program → auto-generate one, then redirect
    if active_program is None:
        from web.program_generator import auto_generate_program
        active_program = auto_generate_program(forge_user, db)

    # Find today's or next upcoming session
    today = date.today()
    sessions = active_program.program_sessions
    today_session = next(
        (s for s in sessions if s.scheduled_date == today and not s.completed_at),
        None,
    )
    if today_session is None:
        upcoming = sorted(
            [s for s in sessions if s.scheduled_date and s.scheduled_date >= today and not s.completed_at],
            key=lambda s: s.scheduled_date,
        )
        today_session = upcoming[0] if upcoming else None

    if today_session is not None:
        return RedirectResponse(
            f"/my/programs/{active_program.id}/sessions/{today_session.id}",
            status_code=303,
        )

    # All sessions completed — redirect to program detail
    return RedirectResponse(f"/my/programs/{active_program.id}", status_code=303)
```

- [ ] **Step 4: Run test**

```bash
pytest tests/test_onboarding.py::test_root_authenticated_no_questionnaire_redirects_to_onboarding -v
```

Expected: `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add web/app.py tests/test_onboarding.py
git commit -m "feat(routing): / always redirects to onboarding or active session"
```

---

## Task 6: New `POST /register` Route (Sign-Up Card)

**Files:**
- Modify: `web/routes_auth.py`

- [ ] **Step 1: Add the new register route to `web/routes_auth.py`**

After the existing `@router.post("/register")` handler (around line 125), add a new route at a **different path** that the sign-up card will POST to. The questionnaire sign-up card will submit to `/register` (no `/auth/` prefix) — add this to `routes_onboarding.py` instead of the auth router so it sits at the root path:

Open `web/routes_onboarding.py` and append:

```python
from web.auth_utils import hash_password, login_session, maybe_migrate_file_token
import os


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, db: Session = Depends(get_db)):
    """Fallback: render a standalone sign-up page if someone hits /register directly."""
    user = get_current_user(request, db)
    if user:
        return RedirectResponse("/", status_code=303)
    # Show the questionnaire at sign-up step (step 9)
    return render_template(
        "questionnaire.html",
        request,
        db=db,
        goal_options=GOAL_OPTIONS,
        age_ranges=AGE_RANGES,
        fitness_levels=FITNESS_LEVELS,
        diet_options=DIET_OPTIONS,
        health_options=HEALTH_OPTIONS,
        equipment_options=EQUIPMENT_OPTIONS,
        days_of_week=DAYS_OF_WEEK,
        is_guest=True,
        is_retake=False,
        start_at_signup=True,   # JS uses this to jump straight to step 9
        existing_goals=_decode(request.session.get("pending_q", {}).get("fitness_goals_json")),
        existing_age_range=request.session.get("pending_q", {}).get("age_range", ""),
        existing_fitness_level=request.session.get("pending_q", {}).get("fitness_level", ""),
        existing_days=_decode(request.session.get("pending_q", {}).get("preferred_days_json")),
        existing_equipment=_decode(request.session.get("pending_q", {}).get("preferred_equipment_json")),
        existing_height_cm=request.session.get("pending_q", {}).get("height_cm"),
        existing_weight_kg=request.session.get("pending_q", {}).get("weight_kg"),
        existing_diet=_decode(request.session.get("pending_q", {}).get("diet_json")),
        existing_health=_decode(request.session.get("pending_q", {}).get("health_conditions_json")),
    )


@router.post("/register")
async def register_from_questionnaire(
    request: Request,
    db: Session = Depends(get_db),
):
    """Create account from the questionnaire sign-up card.

    Reads email + password from form; reads questionnaire answers from
    session["pending_q"] (set by POST /onboarding).
    """
    from web.models import User as _User

    form = await request.form()
    email = str(form.get("email", "")).strip().lower()
    password = str(form.get("password", ""))

    google_enabled = bool(
        os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET")
    )

    def _err(msg: str):
        pending = request.session.get("pending_q", {})
        return render_template(
            "questionnaire.html",
            request,
            db=db,
            goal_options=GOAL_OPTIONS,
            age_ranges=AGE_RANGES,
            fitness_levels=FITNESS_LEVELS,
            diet_options=DIET_OPTIONS,
            health_options=HEALTH_OPTIONS,
            equipment_options=EQUIPMENT_OPTIONS,
            days_of_week=DAYS_OF_WEEK,
            is_guest=True,
            is_retake=False,
            start_at_signup=True,
            flash_error=msg,
            existing_goals=_decode(pending.get("fitness_goals_json")),
            existing_age_range=pending.get("age_range", ""),
            existing_fitness_level=pending.get("fitness_level", ""),
            existing_days=_decode(pending.get("preferred_days_json")),
            existing_equipment=_decode(pending.get("preferred_equipment_json")),
            existing_height_cm=pending.get("height_cm"),
            existing_weight_kg=pending.get("weight_kg"),
            existing_diet=_decode(pending.get("diet_json")),
            existing_health=_decode(pending.get("health_conditions_json")),
        )

    if not email or "@" not in email:
        return _err("Please enter a valid email address.")
    if len(password) < 8:
        return _err("Password must be at least 8 characters.")
    if db.query(_User).filter_by(email=email).first():
        return _err("An account with this email already exists.")

    user = _User(
        email=email,
        hashed_password=hash_password(password),
        is_verified=False,
    )
    db.add(user)
    db.flush()  # get user.id

    # Apply questionnaire answers from session
    pending = request.session.pop("pending_q", {})
    if pending:
        _apply_answers(user, pending)
    user.questionnaire_completed = True  # type: ignore[assignment]

    db.commit()
    db.refresh(user)

    maybe_migrate_file_token(user, db)
    login_session(request, user, db)

    # Auto-generate 8-week program
    auto_generate_program(user, db)

    return RedirectResponse("/", status_code=303)
```

- [ ] **Step 2: Also update the existing `POST /auth/register`** to consume `session["pending_q"]` if present and redirect to `/onboarding` instead of `/my/questionnaire`.

In `web/routes_auth.py`, find the `register_submit` function and change the bottom portion:

```python
    # (existing validation and user creation code stays the same)
    user = User(
        email=email,
        hashed_password=hash_password(password),
        display_name=display_name.strip() or None,
        is_verified=False,
    )
    db.add(user)
    db.flush()

    # Consume any pending questionnaire answers
    pending = request.session.pop("pending_q", {})
    if pending:
        from web.routes_onboarding import _apply_answers
        _apply_answers(user, pending)
        user.questionnaire_completed = True  # type: ignore[assignment]

    db.commit()
    db.refresh(user)

    maybe_migrate_file_token(user, db)
    login_session(request, user, db)

    if user.questionnaire_completed:
        from web.program_generator import auto_generate_program
        auto_generate_program(user, db)
        return RedirectResponse("/", status_code=303)
    return RedirectResponse("/onboarding", status_code=303)
```

- [ ] **Step 3: Update Google and Apple OAuth callbacks**

In `web/routes_auth.py`, change every `return RedirectResponse("/my/questionnaire", ...)` to:

```python
return RedirectResponse("/onboarding", status_code=303)
```

This appears in `google_callback` (line ~254) and `apple_callback` (line ~437).

- [ ] **Step 4: Run full test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: all existing tests pass, no new failures.

- [ ] **Step 5: Commit**

```bash
git add web/routes_onboarding.py web/routes_auth.py tests/test_onboarding.py
git commit -m "feat(auth): POST /register from questionnaire sign-up card; consume pending_q on all sign-up paths"
```

---

## Task 7: Redirect `/my/questionnaire` and Remove Skip

**Files:**
- Modify: `web/routes_my.py:92-156`

- [ ] **Step 1: Replace questionnaire routes with redirects**

In `web/routes_my.py`, replace the three questionnaire route handlers (`questionnaire_page`, `questionnaire_submit`, `questionnaire_skip`) with:

```python
@router.get("/questionnaire")
async def questionnaire_redirect_get(request: Request):
    return RedirectResponse("/onboarding", status_code=301)


@router.post("/questionnaire")
async def questionnaire_redirect_post(request: Request):
    return RedirectResponse("/onboarding", status_code=303)
```

Also remove the import of `GOAL_OPTIONS`, `FITNESS_LEVELS` from this file if they are no longer used (they've moved to `routes_onboarding.py`). Keep `DIET_OPTIONS`, `HEALTH_OPTIONS`, `FITNESS_LEVEL_KEYS` if used by the profile page.

- [ ] **Step 2: Run lint check**

```bash
ruff check web/routes_my.py
```

Expected: no errors (fix any unused import warnings).

- [ ] **Step 3: Run tests**

```bash
pytest tests/ -v --tb=short
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add web/routes_my.py
git commit -m "feat(routes): redirect /my/questionnaire to /onboarding; remove skip endpoint"
```

---

## Task 8: Rewrite `questionnaire.html` Template

**Files:**
- Modify: `web/templates/questionnaire.html`

This is the largest task. The template is rewritten to support 9 steps. Read the full existing file before editing.

**Step order:**
1. Goal (image cards)
2. Age range (large-text cards)
3. Fitness level (radio cards)
4. Preferred training days (day pills)
5. Equipment (tag cloud)
6. Height & Weight (two inputs + metric/imperial toggle)
7. Diet (2-col grid)
8. Health conditions (2-col grid)
9. Sign-up card (guests only — `is_guest=True`)

- [ ] **Step 1: Read the current template**

```bash
# Read web/templates/questionnaire.html in full before making any changes.
```

- [ ] **Step 2: Replace the template**

Write the new `web/templates/questionnaire.html`. Keep the existing CSS classes (`.wcard`, `.wopt`, `.wtag`, `.wnav`, etc.) and add new classes for the new step types. The full template:

```html
{% extends "base.html" %}
{% block title %}Koda — {% if is_retake %}Update Your Profile{% else %}Build Your Plan{% endif %}{% endblock %}

{% block extra_head %}
<style>
/* ── Wizard shell ───────────────────────────────────────────────── */
.wizard-outer { max-width: 480px; margin: 0 auto; padding: 32px 16px 64px; }
.wizard-meta  { display: flex; justify-content: space-between; font-size: 11px; color: #666; margin-bottom: 6px; }
.wizard-track { height: 4px; background: #1e2030; border-radius: 2px; margin-bottom: 28px; }
.wizard-fill  { height: 4px; background: #7c3aed; border-radius: 2px; transition: width .4s ease; }
.wizard-stage { position: relative; min-height: 380px; }

/* ── Cards ──────────────────────────────────────────────────────── */
.wcard {
  background: #1a1d2e; border: 1px solid #2a2d40; border-radius: 16px;
  padding: 26px 24px; position: absolute; top: 0; left: 0; right: 0;
  opacity: 0; transform: scale(.94) translateY(14px);
  pointer-events: none; transition: opacity .3s ease, transform .3s ease;
}
.wcard.active  { opacity: 1; transform: none; pointer-events: all; position: relative; }
.wcard.exiting { opacity: 0; transform: scale(.94) translateY(-10px);
  position: absolute; top: 0; left: 0; right: 0; pointer-events: none; }
.wcard-label { font-size: 11px; font-weight: 600; color: #7c3aed;
  text-transform: uppercase; letter-spacing: .07em; margin-bottom: 8px; }
.wcard-title { font-size: 20px; font-weight: 700; color: #fff; margin-bottom: 6px; line-height: 1.3; }
.wcard-sub   { font-size: 13px; color: #666; margin-bottom: 20px; }

/* ── Goal image cards ───────────────────────────────────────────── */
.goal-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.goal-card { position: relative; border-radius: 12px; overflow: hidden;
  cursor: pointer; border: 2px solid transparent;
  transition: border-color .18s; aspect-ratio: 4/3; }
.goal-card img { width: 100%; height: 100%; object-fit: cover; object-position: top;
  display: block; filter: brightness(.75); transition: filter .18s; }
.goal-card-label { position: absolute; bottom: 0; left: 0; right: 0;
  padding: 8px 10px; background: linear-gradient(transparent, rgba(0,0,0,.7));
  font-size: 13px; font-weight: 600; color: #fff; }
.goal-card:has(input:checked) { border-color: #7c3aed; }
.goal-card:has(input:checked) img { filter: brightness(.9); }
.goal-card:has(input:checked) .goal-card-label::after {
  content: "✓"; float: right; color: #a78bfa; }
.goal-card input { display: none; }

/* ── Age range cards ────────────────────────────────────────────── */
.age-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.age-card { background: #13151f; border: 2px solid #252840; border-radius: 12px;
  padding: 20px 16px; text-align: center; cursor: pointer;
  transition: border-color .18s, background .18s; }
.age-card-range { font-size: 28px; font-weight: 800; color: #7c3aed; line-height: 1; }
.age-card-label { font-size: 12px; color: #666; margin-top: 4px; }
.age-card:has(input:checked) { border-color: #7c3aed; background: #7c3aed18; }
.age-card:has(input:checked) .age-card-range { color: #a78bfa; }
.age-card input { display: none; }

/* ── Day picker ─────────────────────────────────────────────────── */
.day-picker { display: flex; flex-wrap: wrap; gap: 8px; }
.day-pill { background: #13151f; border: 1.5px solid #252840; border-radius: 20px;
  padding: 8px 16px; font-size: 13px; font-weight: 600; color: #aaa; cursor: pointer;
  transition: border-color .18s, background .18s, color .18s; user-select: none; }
.day-pill:has(input:checked) { border-color: #7c3aed; background: #7c3aed22; color: #fff; }
.day-pill input { display: none; }

/* ── Height/Weight ──────────────────────────────────────────────── */
.unit-toggle { display: flex; gap: 0; margin-bottom: 20px; border-radius: 8px; overflow: hidden;
  border: 1.5px solid #252840; width: fit-content; }
.unit-btn { background: transparent; border: none; padding: 6px 18px; font-size: 12px;
  font-weight: 600; color: #666; cursor: pointer; transition: background .18s, color .18s; }
.unit-btn.active { background: #7c3aed; color: #fff; }
.hw-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.hw-field label { display: block; font-size: 11px; color: #666;
  text-transform: uppercase; letter-spacing: .06em; margin-bottom: 6px; }
.hw-input { width: 100%; background: #13151f; border: 1.5px solid #252840;
  border-radius: 10px; padding: 10px 14px; font-size: 18px; font-weight: 700;
  color: #fff; outline: none; transition: border-color .18s; }
.hw-input:focus { border-color: #7c3aed; }
.hw-unit { font-size: 12px; color: #666; margin-top: 4px; }

/* ── Option cards (existing) ───────────────────────────────────── */
.wopts       { display: flex; flex-direction: column; gap: 8px; }
.wopts--row  { flex-direction: row; }
.wopts--grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.wopt { display: flex; align-items: center; background: #13151f;
  border: 1.5px solid #252840; border-radius: 10px; padding: 11px 16px;
  font-size: 14px; color: #bbb; cursor: pointer;
  transition: border-color .18s, background .18s, color .18s; user-select: none; }
.wopts--row  .wopt { flex: 1; justify-content: center; }
.wopts--grid .wopt { font-size: 13px; padding: 10px 12px; }
.wopt:has(input:checked) { border-color: #7c3aed; background: #7c3aed18; color: #fff; }
.wopt input { display: none; }

/* ── Equipment tag cloud (existing) ───────────────────────────── */
.wtags { display: flex; flex-wrap: wrap; gap: 7px; }
.wtag { display: inline-flex; align-items: center; background: #13151f;
  border: 1.5px solid #252840; border-radius: 20px; padding: 6px 14px;
  font-size: 13px; color: #bbb; cursor: pointer;
  transition: border-color .18s, background .18s, color .18s; user-select: none; }
.wtag:has(input:checked) { border-color: #7c3aed; background: #7c3aed22; color: #fff; }
.wtag input { display: none; }

/* ── Nav buttons ────────────────────────────────────────────────── */
.wnav { display: flex; gap: 10px; margin-top: 22px; }
.wnav-back { flex: 1; background: transparent; border: 1.5px solid #252840;
  border-radius: 10px; padding: 10px 14px; color: #666; font-size: 13px;
  cursor: pointer; transition: border-color .18s, color .18s; }
.wnav-back:hover { border-color: #444; color: #aaa; }
.wnav-next, .wnav-save { flex: 2.5; background: #7c3aed; border: none;
  border-radius: 10px; padding: 10px 14px; color: #fff; font-size: 14px;
  font-weight: 600; cursor: pointer; transition: background .18s; }
.wnav-next:hover, .wnav-save:hover { background: #6d28d9; }

/* ── Login link (step 1 guest) ──────────────────────────────────── */
.already-registered { text-align: center; margin-top: 14px; font-size: 13px; color: #555; }
.already-registered a { color: #7c3aed; text-decoration: none; }
.already-registered a:hover { text-decoration: underline; }

/* ── Progress dots ──────────────────────────────────────────────── */
.wdots { display: flex; justify-content: center; gap: 6px; margin-top: 20px; }
.wdot { width: 6px; height: 6px; border-radius: 50%; background: #252840;
  transition: background .3s, transform .3s; }
.wdot.done    { background: #7c3aed88; }
.wdot.current { background: #7c3aed; transform: scale(1.4); }

/* ── Sign-up card ───────────────────────────────────────────────── */
.signup-divider { display: flex; align-items: center; gap: 10px; margin: 16px 0; color: #444; font-size: 12px; }
.signup-divider::before, .signup-divider::after { content: ""; flex: 1; height: 1px; background: #252840; }
.google-btn { width: 100%; background: #fff; border: none; border-radius: 10px;
  padding: 10px 14px; font-size: 14px; font-weight: 600; color: #222;
  cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; }
.google-btn:hover { background: #f0f0f0; }
.wfield { margin-bottom: 14px; }
.wfield label { display: block; font-size: 11px; color: #666;
  text-transform: uppercase; letter-spacing: .06em; margin-bottom: 6px; }
.wfield input { width: 100%; background: #13151f; border: 1.5px solid #252840;
  border-radius: 10px; padding: 10px 14px; font-size: 14px; color: #fff;
  outline: none; transition: border-color .18s; }
.wfield input:focus { border-color: #7c3aed; }
.signup-fine { text-align: center; font-size: 12px; color: #555; margin-top: 12px; }
.signup-fine a { color: #7c3aed; text-decoration: none; }
</style>
{% endblock %}

{% block content %}
<div class="wizard-outer">

  {# Flash error #}
  {% if flash_error %}
  <div style="background:#2d1515;border:1px solid #7f1d1d;border-radius:10px;
              padding:12px 16px;font-size:13px;color:#fca5a5;margin-bottom:20px;">
    {{ flash_error }}
  </div>
  {% endif %}

  {# Progress bar #}
  <div class="wizard-meta">
    <span id="stepLabel">Question 1 of {{ 9 if is_guest else 8 }}</span>
    <span id="stepPct">0%</span>
  </div>
  <div class="wizard-track"><div class="wizard-fill" id="wizFill" style="width:0%"></div></div>

  <form method="post" action="/onboarding" id="wizForm">

  {# ── Hidden fields for collected answers ── #}
  <input type="hidden" name="fitness_goals"   id="hGoals">
  <input type="hidden" name="age_range"        id="hAgeRange">
  <input type="hidden" name="fitness_level"    id="hFitnessLevel">
  <input type="hidden" name="preferred_days"   id="hDays">
  <input type="hidden" name="height_cm"        id="hHeightCm">
  <input type="hidden" name="weight_kg"        id="hWeightKg">

  <div class="wizard-stage" id="wizStage">

    {# ───────────────────────────────── STEP 1: GOAL ── #}
    <div class="wcard" id="card0">
      <div class="wcard-label">Step 1</div>
      <div class="wcard-title">What's your main goal?</div>
      <div class="goal-grid">
        {% for g in goal_options %}
        <label class="goal-card">
          <input type="radio" name="goal_pick" value="{{ g.value }}"
            {% if g.value in existing_goals %}checked{% endif %}>
          <img src="{{ g.image }}" alt="{{ g.label }}" loading="lazy">
          <div class="goal-card-label">{{ g.label }}</div>
        </label>
        {% endfor %}
      </div>
      {% if is_guest %}
      <div class="already-registered">
        Already registered? <a href="/auth/login-forge">Log in</a>
      </div>
      {% endif %}
      <div class="wnav">
        <button type="button" class="wnav-next" onclick="nextStep()">Continue</button>
      </div>
    </div>

    {# ───────────────────────────────── STEP 2: AGE RANGE ── #}
    <div class="wcard" id="card1">
      <div class="wcard-label">Step 2</div>
      <div class="wcard-title">How old are you?</div>
      <div class="age-grid">
        {% for r in age_ranges %}
        <label class="age-card">
          <input type="radio" name="age_range_pick" value="{{ r }}"
            {% if r == existing_age_range %}checked{% endif %}>
          <div class="age-card-range">{{ r }}</div>
          <div class="age-card-label">years</div>
        </label>
        {% endfor %}
      </div>
      <div class="wnav">
        <button type="button" class="wnav-back" onclick="prevStep()">Back</button>
        <button type="button" class="wnav-next" onclick="nextStep()">Continue</button>
      </div>
    </div>

    {# ───────────────────────────────── STEP 3: FITNESS LEVEL ── #}
    <div class="wcard" id="card2">
      <div class="wcard-label">Step 3</div>
      <div class="wcard-title">What's your fitness level?</div>
      <div class="wopts wopts--row">
        {% for lvl in fitness_levels %}
        <label class="wopt">
          <input type="radio" name="fitness_level_pick" value="{{ lvl.value }}"
            {% if lvl.value == existing_fitness_level %}checked{% endif %}>
          {{ lvl.label }}
        </label>
        {% endfor %}
      </div>
      <div class="wnav">
        <button type="button" class="wnav-back" onclick="prevStep()">Back</button>
        <button type="button" class="wnav-next" onclick="nextStep()">Continue</button>
      </div>
    </div>

    {# ───────────────────────────────── STEP 4: TRAINING DAYS ── #}
    <div class="wcard" id="card3">
      <div class="wcard-label">Step 4</div>
      <div class="wcard-title">Which days do you prefer to train?</div>
      <div class="wcard-sub">Select all that apply</div>
      <div class="day-picker">
        {% for d in days_of_week %}
        <label class="day-pill">
          <input type="checkbox" name="days_pick" value="{{ d }}"
            {% if d in existing_days %}checked{% endif %}>
          {{ d }}
        </label>
        {% endfor %}
      </div>
      <div class="wnav">
        <button type="button" class="wnav-back" onclick="prevStep()">Back</button>
        <button type="button" class="wnav-next" onclick="nextStep()">Continue</button>
      </div>
    </div>

    {# ───────────────────────────────── STEP 5: EQUIPMENT ── #}
    <div class="wcard" id="card4">
      <div class="wcard-label">Step 5</div>
      <div class="wcard-title">What equipment do you have access to?</div>
      <div class="wtags">
        {% for eq in equipment_options %}
        <label class="wtag">
          <input type="checkbox" name="equipment_pick" value="{{ eq.tag }}"
            {% if eq.tag in existing_equipment %}checked{% endif %}>
          {{ eq.icon }} {{ eq.label }}
        </label>
        {% endfor %}
      </div>
      <div class="wnav">
        <button type="button" class="wnav-back" onclick="prevStep()">Back</button>
        <button type="button" class="wnav-next" onclick="nextStep()">Continue</button>
      </div>
    </div>

    {# ───────────────────────────────── STEP 6: HEIGHT & WEIGHT ── #}
    <div class="wcard" id="card5">
      <div class="wcard-label">Step 6</div>
      <div class="wcard-title">Your body stats</div>
      <div class="wcard-sub">Used to personalise your plan. Optional.</div>

      <div class="unit-toggle">
        <button type="button" class="unit-btn active" id="btnMetric" onclick="setUnit('metric')">Metric</button>
        <button type="button" class="unit-btn" id="btnImperial" onclick="setUnit('imperial')">Imperial</button>
      </div>

      <div class="hw-row">
        <div class="hw-field">
          <label id="heightLabel">Height</label>
          <input class="hw-input" type="number" id="heightInput" placeholder="—" min="100" max="250" step="1"
                 value="{{ existing_height_cm or '' }}">
          <div class="hw-unit" id="heightUnit">cm</div>
        </div>
        <div class="hw-field">
          <label id="weightLabel">Weight</label>
          <input class="hw-input" type="number" id="weightInput" placeholder="—" min="30" max="300" step="0.5"
                 value="{{ existing_weight_kg or '' }}">
          <div class="hw-unit" id="weightUnit">kg</div>
        </div>
      </div>

      <div class="wnav">
        <button type="button" class="wnav-back" onclick="prevStep()">Back</button>
        <button type="button" class="wnav-next" onclick="nextStep()">Continue</button>
      </div>
    </div>

    {# ───────────────────────────────── STEP 7: DIET ── #}
    <div class="wcard" id="card6">
      <div class="wcard-label">Step 7</div>
      <div class="wcard-title">Any dietary preferences?</div>
      <div class="wopts wopts--grid">
        {% for d in diet_options %}
        <label class="wopt">
          <input type="checkbox" name="diet_pick" value="{{ d.value }}"
            {% if d.value in existing_diet %}checked{% endif %}>
          {{ d.label }}
        </label>
        {% endfor %}
      </div>
      <div class="wnav">
        <button type="button" class="wnav-back" onclick="prevStep()">Back</button>
        <button type="button" class="wnav-next" onclick="nextStep()">Continue</button>
      </div>
    </div>

    {# ───────────────────────────────── STEP 8: HEALTH CONDITIONS ── #}
    <div class="wcard" id="card7">
      <div class="wcard-label">Step 8</div>
      <div class="wcard-title">Any health conditions we should know about?</div>
      <div class="wopts wopts--grid">
        {% for h in health_options %}
        <label class="wopt">
          <input type="checkbox" name="health_pick" value="{{ h.value }}"
            {% if h.value in existing_health %}checked{% endif %}>
          {{ h.label }}
        </label>
        {% endfor %}
      </div>
      <div class="wnav">
        <button type="button" class="wnav-back" onclick="prevStep()">Back</button>
        {% if is_guest %}
        <button type="button" class="wnav-next" onclick="nextStep()">Continue</button>
        {% else %}
        <button type="button" class="wnav-save" onclick="submitForm()">Save Profile</button>
        {% endif %}
      </div>
    </div>

    {# ───────────────────────────────── STEP 9: SIGN-UP (guests only) ── #}
    {% if is_guest %}
    <div class="wcard" id="card8">
      <div class="wcard-label">Almost There</div>
      <div class="wcard-title">Your plan is ready.</div>
      <div class="wcard-sub">Create a free account to unlock it.</div>

      <a href="/auth/google" class="google-btn" style="display:flex;text-decoration:none;margin-bottom:4px;">
        <svg width="18" height="18" viewBox="0 0 18 18"><path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z"/><path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z"/><path fill="#FBBC05" d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z"/><path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z"/></svg>
        Continue with Google
      </a>

      <div class="signup-divider">or</div>

      {# Email/password fields live inside the outer #wizForm — no nested form.
         JS changes wizForm's action to /register when this step is active. #}
      <input type="hidden" name="_from_questionnaire" value="1">
      <div class="wfield">
        <label>Email</label>
        <input type="email" name="email" id="signupEmail" placeholder="you@example.com" autocomplete="email">
      </div>
      <div class="wfield">
        <label>Password</label>
        <input type="password" name="password" id="signupPassword" placeholder="8+ characters" autocomplete="new-password">
      </div>
      <button type="button" class="wnav-save" style="width:100%;border-radius:10px;padding:12px;"
              onclick="submitSignup()">
        Create account &amp; start training
      </button>

      <div class="signup-fine">Already have an account? <a href="/auth/login-forge">Log in</a></div>
      <div class="wnav" style="margin-top:10px;">
        <button type="button" class="wnav-back" onclick="prevStep()">Back</button>
      </div>
    </div>
    {% endif %}

  </div>{# /wizard-stage #}
  </form>

  {# Progress dots #}
  <div class="wdots" id="wizDots"></div>

</div>{# /wizard-outer #}

<script>
(function () {
  const TOTAL = {{ 9 if is_guest else 8 }};
  const START_AT = {{ (TOTAL - 1) if (start_at_signup is defined and start_at_signup) else 0 }};
  let cur = START_AT;

  // ── DOM refs ────────────────────────────────────────────────────
  const cards   = Array.from(document.querySelectorAll('.wcard'));
  const fill    = document.getElementById('wizFill');
  const label   = document.getElementById('stepLabel');
  const pct     = document.getElementById('stepPct');
  const dotsEl  = document.getElementById('wizDots');

  // ── Build dots ──────────────────────────────────────────────────
  for (let i = 0; i < TOTAL; i++) {
    const d = document.createElement('span');
    d.className = 'wdot';
    dotsEl.appendChild(d);
  }
  function updateDots() {
    dotsEl.querySelectorAll('.wdot').forEach((d, i) => {
      d.className = 'wdot' + (i < cur ? ' done' : i === cur ? ' current' : '');
    });
  }

  // ── Progress bar ─────────────────────────────────────────────────
  function updateProgress() {
    const p = Math.round((cur / (TOTAL - 1)) * 100);
    fill.style.width = p + '%';
    label.textContent = `Question ${cur + 1} of ${TOTAL}`;
    pct.textContent = p + '%';
    updateDots();
  }

  // ── Show card ────────────────────────────────────────────────────
  function showCard(idx) {
    cards.forEach((c, i) => {
      if (i === idx) { c.classList.add('active'); c.classList.remove('exiting'); }
      else           { c.classList.remove('active'); }
    });
    updateProgress();
  }

  // ── Collect current card answers ─────────────────────────────────
  function collectCard(idx) {
    const card = cards[idx];
    switch (idx) {
      case 0: // goal
        const gPick = card.querySelector('input[name="goal_pick"]:checked');
        if (gPick) document.getElementById('hGoals').name = 'fitness_goals';
        document.getElementById('hGoals').value = gPick ? gPick.value : '';
        break;
      case 1: // age range
        const aPick = card.querySelector('input[name="age_range_pick"]:checked');
        document.getElementById('hAgeRange').value = aPick ? aPick.value : '';
        break;
      case 2: // fitness level
        const lvPick = card.querySelector('input[name="fitness_level_pick"]:checked');
        document.getElementById('hFitnessLevel').value = lvPick ? lvPick.value : '';
        break;
      case 3: // days
        const dayChecked = Array.from(card.querySelectorAll('input[name="days_pick"]:checked')).map(x => x.value);
        document.getElementById('hDays').value = dayChecked.join(',');
        break;
      case 4: // equipment — checkbox inputs submit directly via name="equipment"
        break;
      case 5: // height/weight — stored via collectHeightWeight()
        collectHeightWeight();
        break;
      case 6: // diet — checkbox inputs submit directly via name="diet_pick" — rename
        break;
      case 7: // health — checkbox inputs submit directly
        break;
    }
  }

  // ── Fix checkbox names before submit ─────────────────────────────
  function fixCheckboxNames() {
    document.querySelectorAll('input[name="equipment_pick"]').forEach(el => el.name = 'equipment');
    document.querySelectorAll('input[name="diet_pick"]').forEach(el => el.name = 'diet');
    document.querySelectorAll('input[name="health_pick"]').forEach(el => el.name = 'health_conditions');
    // Convert days hidden field to multiple hidden inputs
    const daysVal = document.getElementById('hDays').value;
    if (daysVal) {
      daysVal.split(',').forEach(d => {
        const inp = document.createElement('input');
        inp.type = 'hidden'; inp.name = 'preferred_days'; inp.value = d;
        document.getElementById('wizForm').appendChild(inp);
      });
    }
    document.getElementById('hDays').disabled = true;
    // Fitness goals hidden field → multiple hidden input
    const goalVal = document.getElementById('hGoals').value;
    if (goalVal) {
      const inp = document.createElement('input');
      inp.type = 'hidden'; inp.name = 'fitness_goals'; inp.value = goalVal;
      document.getElementById('wizForm').appendChild(inp);
    }
    document.getElementById('hGoals').disabled = true;
  }

  // ── Navigation ───────────────────────────────────────────────────
  window.nextStep = function () {
    collectCard(cur);
    const exiting = cards[cur];
    exiting.classList.add('exiting');
    setTimeout(() => exiting.classList.remove('exiting', 'active'), 320);
    cur = Math.min(cur + 1, TOTAL - 1);
    showCard(cur);
    // If entering the sign-up step, point the form to /register
    const isGuest = {{ 'true' if is_guest else 'false' }};
    if (isGuest && cur === TOTAL - 1) {
      document.getElementById('wizForm').action = '/register';
    }
  };

  window.prevStep = function () {
    const exiting = cards[cur];
    exiting.classList.add('exiting');
    setTimeout(() => exiting.classList.remove('exiting', 'active'), 320);
    cur = Math.max(cur - 1, 0);
    showCard(cur);
  };

  window.submitForm = function () {
    // Collect all cards first
    for (let i = 0; i < TOTAL; i++) collectCard(i);
    fixCheckboxNames();
    document.getElementById('wizForm').submit();
  };

  // Sign-up submit (guests, step 9)
  window.submitSignup = function () {
    const email = document.getElementById('signupEmail').value.trim();
    const pwd   = document.getElementById('signupPassword').value;
    if (!email || !email.includes('@')) { alert('Please enter a valid email.'); return; }
    if (pwd.length < 8) { alert('Password must be at least 8 characters.'); return; }
    // Collect all previous steps' answers
    for (let i = 0; i < TOTAL - 1; i++) collectCard(i);
    fixCheckboxNames();
    const form = document.getElementById('wizForm');
    form.action = '/register';
    form.submit();
  };

  // ── Height / Weight unit handling ────────────────────────────────
  let currentUnit = 'metric';
  let heightCm = null;
  let weightKg = null;

  window.setUnit = function (unit) {
    currentUnit = unit;
    const hInput = document.getElementById('heightInput');
    const wInput = document.getElementById('weightInput');
    document.getElementById('btnMetric').classList.toggle('active', unit === 'metric');
    document.getElementById('btnImperial').classList.toggle('active', unit === 'imperial');

    if (unit === 'imperial') {
      document.getElementById('heightUnit').textContent = 'ft / in';
      document.getElementById('weightUnit').textContent = 'lbs';
      hInput.placeholder = '5.9';
      hInput.step = '0.1';
      if (heightCm) hInput.value = (heightCm / 30.48).toFixed(1);
      if (weightKg) wInput.value = (weightKg * 2.2046).toFixed(1);
    } else {
      document.getElementById('heightUnit').textContent = 'cm';
      document.getElementById('weightUnit').textContent = 'kg';
      hInput.placeholder = '175';
      hInput.step = '1';
      if (heightCm) hInput.value = Math.round(heightCm);
      if (weightKg) wInput.value = weightKg.toFixed(1);
    }
  };

  function collectHeightWeight() {
    const hVal = parseFloat(document.getElementById('heightInput').value);
    const wVal = parseFloat(document.getElementById('weightInput').value);
    if (!isNaN(hVal)) {
      heightCm = currentUnit === 'imperial' ? hVal * 30.48 : hVal;
    }
    if (!isNaN(wVal)) {
      weightKg = currentUnit === 'imperial' ? wVal / 2.2046 : wVal;
    }
    document.getElementById('hHeightCm').value = heightCm ? heightCm.toFixed(1) : '';
    document.getElementById('hWeightKg').value = weightKg ? weightKg.toFixed(1) : '';
  }

  // ── Init ─────────────────────────────────────────────────────────
  showCard(cur);

  // Pre-populate height/weight from server values
  const initH = {{ existing_height_cm or 'null' }};
  const initW = {{ existing_weight_kg or 'null' }};
  if (initH) { heightCm = initH; document.getElementById('heightInput').value = Math.round(initH); }
  if (initW) { weightKg = initW; document.getElementById('weightInput').value = initW.toFixed(1); }

})();
</script>
{% endblock %}
```

- [ ] **Step 3: Smoke test in browser**

Start the server and navigate to `http://localhost:8000/` without being logged in. Verify:
- You land on `/onboarding`
- Step 1 shows 6 goal image cards
- "Already registered? Log in" link is visible
- Clicking a card advances to step 2
- Age range shows 4 cards (18-29, 30-39, 40-49, 50+)
- Day picker shows Mon–Sun pills
- Height/Weight step has metric/imperial toggle
- Progress bar advances through all 8 steps
- Step 9 shows sign-up card with Google button + email/password form

- [ ] **Step 4: Commit**

```bash
git add web/templates/questionnaire.html
git commit -m "feat(ui): redesign questionnaire — goal image cards, age ranges, day picker, height/weight, sign-up card"
```

---

## Task 9: Session Preview — Exercise Rows & Nutrition Card

**Files:**
- Modify: `web/templates/my_session_preview.html`

- [ ] **Step 1: Read the full session preview template**

```bash
# Read web/templates/my_session_preview.html in full before editing
```

- [ ] **Step 2: Add exercise thumbnail rows CSS**

In the template's `{% block extra_head %}`, add:

```html
<style>
/* ── Exercise thumbnail rows ───────────────────────────────────── */
.exercise-row {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 0; border-bottom: 1px solid #1e2030;
}
.exercise-row:last-child { border-bottom: none; }
.exercise-thumb {
  width: 44px; height: 44px; border-radius: 8px; flex-shrink: 0;
  background: linear-gradient(135deg, #1e2030 0%, #252840 100%);
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; color: #3a3d58; overflow: hidden;
}
.exercise-thumb img { width: 100%; height: 100%; object-fit: cover; border-radius: 8px; }
.exercise-row-info { flex: 1; min-width: 0; }
.exercise-row-name { font-size: 14px; font-weight: 600; color: #e2e8f0;
  display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.exercise-row-meta { display: flex; gap: 4px; margin-top: 4px; align-items: center; }
.set-pip { width: 8px; height: 8px; border-radius: 50%; background: #22c55e; flex-shrink: 0; }
.set-pip--rest { background: #3b82f6; }
.exercise-row-sets { font-size: 11px; color: #666; margin-left: 4px; }

/* ── Nutrition coming-soon card ────────────────────────────────── */
.nutrition-card {
  background: #1a1d2e; border: 1px dashed #2a2d40; border-radius: 16px;
  padding: 24px; text-align: center; position: relative; overflow: hidden;
}
.nutrition-card::before {
  content: ""; position: absolute; inset: 0;
  background: repeating-linear-gradient(
    45deg, transparent, transparent 8px,
    rgba(42,45,64,.3) 8px, rgba(42,45,64,.3) 9px
  );
}
.nutrition-card > * { position: relative; z-index: 1; }
.coming-soon-badge {
  display: inline-block; background: #252840; border: 1px solid #3a3d58;
  border-radius: 20px; padding: 3px 12px; font-size: 11px; font-weight: 600;
  color: #666; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 12px;
}
.nutrition-placeholder-row {
  height: 12px; border-radius: 6px; background: #1e2030; margin: 8px auto;
}
</style>
```

- [ ] **Step 3: Add exercise mini-list before the existing circuit layout**

Find the existing exercise list section in the template (inside `.koda-card--active`). Before the existing `{% for exercise in exercises %}` loop, insert a mini-list block:

```html
{# ── Mini exercise preview (first 5) ── #}
<div class="mb-4">
  <div class="koda-section-label mb-2">Exercises</div>
  {% for ex in exercises[:5] %}
  <div class="exercise-row">
    <div class="exercise-thumb">
      {% if ex.video_url and ex.video_url.startswith('/static') %}
        {# local video — use poster frame placeholder #}
        <span style="font-size:10px;color:#555;">▶</span>
      {% else %}
        <span>🏋️</span>
      {% endif %}
    </div>
    <div class="exercise-row-info">
      <span class="exercise-row-name">{{ ex.label }}</span>
      <div class="exercise-row-meta">
        {% for _ in range(ex.sets) %}<span class="set-pip"></span>{% endfor %}
        <span class="exercise-row-sets">
          {{ ex.sets }}×{% if ex.reps %}{{ ex.reps }}{% else %}{{ (ex.duration_sec|int) }}s{% endif %}
        </span>
      </div>
    </div>
  </div>
  {% endfor %}
  {% if exercises|length > 5 %}
  <div style="text-align:center;font-size:12px;color:#555;margin-top:8px;">
    +{{ exercises|length - 5 }} more exercises
  </div>
  {% endif %}
</div>
```

- [ ] **Step 4: Add nutrition coming-soon card at the bottom of the right column**

Find the right column in the template (`.col-12 col-lg-4`). At the end of that column, append:

```html
{# ── Today's Nutrition — Coming Soon ── #}
<div class="nutrition-card mt-4">
  <div class="coming-soon-badge">Coming Soon</div>
  <h3 style="font-size:16px;font-weight:700;color:#e2e8f0;margin-bottom:6px;">Today's Nutrition</h3>
  <p style="font-size:13px;color:#555;margin-bottom:16px;">
    Personalised meal plan based on your goals.
  </p>
  <div class="nutrition-placeholder-row" style="width:80%;"></div>
  <div class="nutrition-placeholder-row" style="width:65%;"></div>
  <div class="nutrition-placeholder-row" style="width:72%;"></div>
</div>
```

- [ ] **Step 5: Smoke test in browser**

Log in → navigate to an active program session. Verify:
- Mini exercise list appears with thumbnail placeholders and set pip dots
- Nutrition card appears below the muscle map column with dashed border and "Coming Soon" badge

- [ ] **Step 6: Commit**

```bash
git add web/templates/my_session_preview.html
git commit -m "feat(ui): session preview — exercise thumbnail rows + nutrition coming-soon card"
```

---

## Task 10: End-to-End Verification

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: all tests pass.

- [ ] **Step 2: Test guest flow in browser (incognito)**

1. Open `http://localhost:8000/` → redirects to `/onboarding`
2. Complete all 8 steps → step 9 shows sign-up card
3. Submit email + password → account created, program auto-generated, redirected to today's session
4. Session page shows exercise mini-list + nutrition placeholder

- [ ] **Step 3: Test logged-in retake**

1. Log in → navigate to `http://localhost:8000/my/questionnaire` → redirected 301 to `/onboarding`
2. Complete questionnaire → no sign-up card on step 8 → hits "Save Profile" → redirected to `/`
3. If questionnaire not previously completed: auto-program is generated

- [ ] **Step 4: Test Google OAuth new user**

1. Go to `/auth/google` → complete OAuth → redirected to `/onboarding` (not `/my/questionnaire`)
2. Complete questionnaire → saved, program generated, land on session

- [ ] **Step 5: Test `/` routing**

```bash
python -c "
import requests
# Unauthenticated
r = requests.get('http://localhost:8000/', allow_redirects=False)
assert r.status_code in (302, 303) and 'onboarding' in r.headers['location'], r.headers
print('/ unauthenticated: OK')
"
```

- [ ] **Step 6: Lint**

```bash
ruff check web/
ruff format --check web/
```

Expected: no errors. Fix any lint warnings before final commit.

- [ ] **Step 7: Final commit**

```bash
git add -A
git commit -m "feat: onboarding questionnaire redesign + auto-program generation + session home screen"
```
