# Fitness Rank & Health-Condition Filtering — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dynamic 1–10 fitness rank per user (seeded from the questionnaire, self-corrected via mid/post-workout feedback) and hard health-condition exercise exclusions so exercise selection is always safe and appropriately challenging.

**Architecture:** `User.fitness_rank` (float, 1–10) is computed once at questionnaire save and updated via `PATCH /my/rank-feedback`. `workout_generator.py` gains a `difficulty` field on every exercise template, a `_HEALTH_EXCLUSIONS` dict keyed to exact DB condition values, and a rank-band filter applied before the existing muscle-group selection logic. The workout player modal (in `workout_preview.html`) gains mid-workout "Too easy / Too hard" buttons and a post-workout 3-button prompt. The progress page surfaces the prompt for sessions where post-workout feedback was skipped.

**Tech Stack:** Python / FastAPI / SQLAlchemy / Alembic / Jinja2 / vanilla JS (Bootstrap modals)

---

## File Map

| File | Change |
|------|--------|
| `web/models.py` | Add `User.fitness_rank`, add `RankFeedback` model |
| `web/migrations/versions/0005_add_fitness_rank.py` | New Alembic migration |
| `web/workout_generator.py` | `_ExTemplate.difficulty`, full `_POOL` re-annotation, `_HEALTH_EXCLUSIONS`, updated `_select_exercises`, updated `generate()` |
| `web/routes_onboarding.py` | Compute initial `fitness_rank` in `_apply_answers()` |
| `web/routes_my.py` | `PATCH /my/rank-feedback` endpoint |
| `web/app.py` | Pass `fitness_rank` + `health_conditions` into `generate()` |
| `web/templates/questionnaire.html` | Add one-line descriptions per fitness level |
| `web/templates/workout_preview.html` | Mid-workout buttons + post-workout prompt in player modal |
| `web/templates/my_progress.html` | Inline feedback prompt for sessions missing post-workout feedback |
| `web/translations.py` | New translation keys for fitness level descriptions and feedback UI |
| `tests/test_fitness_rank.py` | All new tests for rank logic, health filtering, band selection |

---

## Task 1: Add `User.fitness_rank` + `RankFeedback` model and migration

**Files:**
- Modify: `web/models.py`
- Create: `web/migrations/versions/0005_add_fitness_rank.py`

- [ ] **Step 1.1 — Write the failing test**

Create `tests/test_fitness_rank.py`:

```python
"""Tests for fitness rank data model and rank computation."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from web.db import Base
from web.models import User, RankFeedback


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_user_fitness_rank_defaults_to_none(db):
    u = User(email="a@b.com", hashed_password="x")
    db.add(u)
    db.commit()
    db.refresh(u)
    assert u.fitness_rank is None


def test_rank_feedback_stores_delta(db):
    u = User(email="a@b.com", hashed_password="x")
    db.add(u)
    db.commit()
    rf = RankFeedback(
        user_id=u.id,
        trigger="post_workout",
        feedback="too_easy",
        delta=0.5,
        rank_before=3.0,
        rank_after=3.5,
    )
    db.add(rf)
    db.commit()
    db.refresh(rf)
    assert rf.rank_after == 3.5
    assert rf.trigger == "post_workout"
```

- [ ] **Step 1.2 — Run to confirm it fails**

```
pytest tests/test_fitness_rank.py -v
```

Expected: `ImportError` or `OperationalError` — `RankFeedback` does not exist yet.

- [ ] **Step 1.3 — Add the models**

In `web/models.py`, add after the `User` class `last_login_at` field (before the relationships):

```python
    fitness_rank: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 1.0–10.0, null until questionnaire is completed. Updated via /my/rank-feedback.
```

Then add after the `WorkoutSession` class, before `Program`:

```python
class RankFeedback(Base):
    __tablename__ = "rank_feedbacks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("workout_sessions.id", ondelete="SET NULL"), nullable=True
    )
    trigger: Mapped[str] = mapped_column(String(20), nullable=False)
    # "mid_workout" | "post_workout"
    feedback: Mapped[str] = mapped_column(String(20), nullable=False)
    # "too_easy" | "just_right" | "too_hard"
    delta: Mapped[float] = mapped_column(Float, nullable=False)
    rank_before: Mapped[float] = mapped_column(Float, nullable=False)
    rank_after: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 1.4 — Create the Alembic migration**

Create `web/migrations/versions/0005_add_fitness_rank.py`:

```python
"""add fitness_rank to users and rank_feedbacks table

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-12
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("fitness_rank", sa.Float(), nullable=True))
    op.create_table(
        "rank_feedbacks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("workout_sessions.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("trigger", sa.String(20), nullable=False),
        sa.Column("feedback", sa.String(20), nullable=False),
        sa.Column("delta", sa.Float(), nullable=False),
        sa.Column("rank_before", sa.Float(), nullable=False),
        sa.Column("rank_after", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("rank_feedbacks")
    op.drop_column("users", "fitness_rank")
```

- [ ] **Step 1.5 — Run the tests**

```
pytest tests/test_fitness_rank.py -v
```

Expected: both tests **PASS**.

- [ ] **Step 1.6 — Commit**

```bash
git add web/models.py web/migrations/versions/0005_add_fitness_rank.py tests/test_fitness_rank.py
git commit -m "feat(models): add User.fitness_rank and RankFeedback model + migration"
```

---

## Task 2: Initial rank computation from questionnaire

**Files:**
- Modify: `web/routes_onboarding.py`

> **Key mapping** — DB stores these exact strings for health conditions:
> `"joint_problems"`, `"back_pain"`, `"heart_condition"`, `"asthma"`, `"high_blood_pressure"`, `"diabetes"`
> Fitness level stored as `"Beginner"`, `"Intermediate"`, `"Advanced"` (capital first letter).

- [ ] **Step 2.1 — Write the failing test**

Add to `tests/test_fitness_rank.py`:

```python
from web.routes_onboarding import compute_initial_rank


def test_beginner_gets_low_rank():
    assert compute_initial_rank("Beginner", "18-29", []) == 2.0


def test_intermediate_base():
    assert compute_initial_rank("Intermediate", "30-39", []) == 5.0


def test_advanced_base():
    assert compute_initial_rank("Advanced", "40-49", []) == 8.0


def test_50_plus_penalty():
    assert compute_initial_rank("Intermediate", "50+", []) == 4.0


def test_health_penalty():
    assert compute_initial_rank("Intermediate", "30-39", ["joint_problems"]) == 4.5


def test_50_plus_beginner_with_health():
    # 2.0 - 1.0 - 0.5 = 0.5, clamped to 1.0
    assert compute_initial_rank("Beginner", "50+", ["back_pain"]) == 1.0


def test_advanced_no_penalty():
    assert compute_initial_rank("Advanced", "18-29", []) == 8.0


def test_none_fitness_level_falls_back():
    assert compute_initial_rank(None, None, []) == 3.0


def test_rank_clamped_at_10():
    # Even if hypothetically above 10 — clamped
    assert compute_initial_rank("Advanced", "18-29", []) <= 10.0
```

- [ ] **Step 2.2 — Run to confirm they fail**

```
pytest tests/test_fitness_rank.py::test_beginner_gets_low_rank -v
```

Expected: `ImportError: cannot import name 'compute_initial_rank'`

- [ ] **Step 2.3 — Implement `compute_initial_rank` in `routes_onboarding.py`**

Add this function before `_apply_answers()` in `web/routes_onboarding.py`:

```python
_FITNESS_RANK_BASE: dict[str, float] = {
    "beginner":     2.0,
    "intermediate": 5.0,
    "advanced":     8.0,
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
```

Then inside `_apply_answers()`, after line `user.health_conditions_json = answers.get("health_conditions_json")`, add:

```python
    # Compute fitness rank from questionnaire (always recompute on questionnaire save/retake)
    _conditions = json.loads(user.health_conditions_json or "[]")
    user.fitness_rank = compute_initial_rank(  # type: ignore[assignment]
        user.fitness_level, user.age_range, _conditions
    )
```

- [ ] **Step 2.4 — Run the tests**

```
pytest tests/test_fitness_rank.py -v
```

Expected: all 9 tests **PASS**.

- [ ] **Step 2.5 — Commit**

```bash
git add web/routes_onboarding.py tests/test_fitness_rank.py
git commit -m "feat(onboarding): compute initial fitness_rank from questionnaire answers"
```

---

## Task 3: Add `difficulty` to `_ExTemplate` and annotate all pool exercises

**Files:**
- Modify: `web/workout_generator.py` (lines 129–361)

- [ ] **Step 3.1 — Write the failing test**

Add to `tests/test_fitness_rank.py`:

```python
from web.workout_generator import _POOL


def test_all_pool_exercises_have_difficulty():
    for ex in _POOL:
        assert hasattr(ex, "difficulty"), f"{ex.name} missing difficulty"
        assert 1 <= ex.difficulty <= 10, f"{ex.name} difficulty {ex.difficulty} out of range"
```

- [ ] **Step 3.2 — Run to confirm it fails**

```
pytest tests/test_fitness_rank.py::test_all_pool_exercises_have_difficulty -v
```

Expected: `TypeError` — `_ExTemplate.__init__()` takes no `difficulty` argument.

- [ ] **Step 3.3 — Add `difficulty` field to `_ExTemplate`**

In `web/workout_generator.py`, change the `_ExTemplate` dataclass (around line 129):

```python
@dataclass
class _ExTemplate:
    category:          str
    name:              str
    label:             str
    muscle_group:      str        # push | pull | squat | hinge | lunge | core | arms_bi | arms_tri | shoulders | calves
    tags:              list[str]  # compound | isolation | total_body | core
    equipment:         list[str]  # barbell | dumbbell | cable | machine | kettlebell | bodyweight | band
    primary_muscles:   list[str]  # e.g. ["chest", "triceps"]
    secondary_muscles: list[str]  # e.g. ["front_delt"]
    difficulty:        int        # 1–10: 1–2 beginner, 3–4 light, 5–6 moderate, 7–8 advanced, 9–10 elite
```

- [ ] **Step 3.4 — Replace the entire `_POOL` list with difficulty-annotated entries**

Replace the entire `_POOL` list (lines 169–361 in `web/workout_generator.py`) with the following.
The last argument on every line is the new `difficulty` score:

```python
_POOL: list[_ExTemplate] = [
    # -----------------------------------------------------------------------
    # PUSH — chest compound
    # -----------------------------------------------------------------------
    _ExTemplate("BENCH_PRESS",      "BARBELL_BENCH_PRESS",           "Barbell Bench Press",           "push",      ["compound"], ["barbell"],                         ["chest"],              ["triceps", "front_delt"],           6),
    _ExTemplate("BENCH_PRESS",      "DUMBBELL_BENCH_PRESS",          "Dumbbell Bench Press",          "push",      ["compound"], ["dumbbell"],                        ["chest"],              ["triceps", "front_delt"],           5),
    _ExTemplate("BENCH_PRESS",      "INCLINE_BARBELL_BENCH_PRESS",   "Incline Barbell Bench Press",   "push",      ["compound"], ["barbell"],                         ["chest", "front_delt"],["triceps"],                         6),
    _ExTemplate("BENCH_PRESS",      "INCLINE_DUMBBELL_BENCH_PRESS",  "Incline Dumbbell Bench Press",  "push",      ["compound"], ["dumbbell"],                        ["chest", "front_delt"],["triceps"],                         5),
    _ExTemplate("PUSH_UP",          "PUSH_UP",                       "Push-Up",                       "push",      ["compound"], ["bodyweight", "weight_vest"],       ["chest"],              ["triceps", "front_delt"],           2),
    _ExTemplate("PUSH_UP",          "DIAMOND_PUSH_UP",               "Diamond Push-Up",               "push",      ["compound"], ["bodyweight"],                      ["triceps", "chest"],   ["front_delt"],                      3),
    _ExTemplate("PUSH_UP",          "INCLINE_PUSH_UP",               "Incline Push-Up",               "push",      ["compound"], ["bench", "bodyweight", "bosu_ball"],["chest"],              ["triceps", "front_delt"],           1),
    _ExTemplate("PUSH_UP",          "DECLINE_PUSH_UP",               "Decline Push-Up",               "push",      ["compound"], ["bench", "bodyweight"],             ["chest"],              ["triceps", "front_delt"],           3),
    # PUSH — shoulder compound
    _ExTemplate("SHOULDER_PRESS",   "BARBELL_SHOULDER_PRESS",        "Barbell Shoulder Press",        "push",      ["compound"], ["barbell", "smith_machine"],        ["front_delt"],         ["triceps", "traps"],                7),
    _ExTemplate("SHOULDER_PRESS",   "DUMBBELL_SHOULDER_PRESS",       "Dumbbell Shoulder Press",       "push",      ["compound"], ["dumbbell"],                        ["front_delt"],         ["triceps", "traps"],                5),
    _ExTemplate("SHOULDER_PRESS",   "ARNOLD_PRESS",                  "Arnold Press",                  "push",      ["compound"], ["dumbbell"],                        ["front_delt"],         ["triceps", "traps"],                5),
    # PUSH — chest isolation
    _ExTemplate("FLYE",             "DUMBBELL_FLYE",                 "Dumbbell Flye",                 "push",      ["isolation"], ["dumbbell"],                       ["chest"],              ["front_delt"],                      4),
    _ExTemplate("FLYE",             "CABLE_CROSSOVER",               "Cable Crossover",               "push",      ["isolation"], ["cable"],                          ["chest"],              ["front_delt"],                      4),
    # SHOULDERS isolation
    _ExTemplate("LATERAL_RAISE",    "DUMBBELL_LATERAL_RAISE",        "Dumbbell Lateral Raise",        "shoulders", ["isolation"], ["dumbbell", "band"],               ["front_delt"],         ["traps"],                           2),
    _ExTemplate("LATERAL_RAISE",    "CABLE_LATERAL_RAISE",           "Cable Lateral Raise",           "shoulders", ["isolation"], ["cable"],                          ["front_delt"],         ["traps"],                           3),

    # -----------------------------------------------------------------------
    # PULL — compound
    # -----------------------------------------------------------------------
    _ExTemplate("PULL_UP",          "PULL_UP",                       "Pull-Up",                       "pull",      ["compound"], ["pullup_bar", "weight_vest"],       ["lats"],               ["biceps", "rear_delt"],             7),
    _ExTemplate("PULL_UP",          "CHIN_UP",                       "Chin-Up",                       "pull",      ["compound"], ["pullup_bar"],                      ["lats", "biceps"],     ["rear_delt"],                       6),
    _ExTemplate("PULL_UP",          "WIDE_GRIP_PULL_UP",             "Wide-Grip Pull-Up",             "pull",      ["compound"], ["pullup_bar"],                      ["lats"],               ["rear_delt", "biceps"],             7),
    _ExTemplate("PULL_UP",          "NEUTRAL_GRIP_PULL_UP",          "Neutral-Grip Pull-Up",          "pull",      ["compound"], ["pullup_bar"],                      ["lats"],               ["biceps", "rear_delt"],             6),
    _ExTemplate("PULL_UP",          "BANDED_PULL_UP",                "Banded Pull-Up",                "pull",      ["compound"], ["pullup_bar", "band"],              ["lats"],               ["biceps", "rear_delt"],             4),
    _ExTemplate("PULL_UP",          "LAT_PULLDOWN",                  "Lat Pulldown",                  "pull",      ["compound"], ["cable", "machine"],                ["lats"],               ["biceps"],                          3),
    _ExTemplate("ROW",              "BARBELL_ROW",                   "Barbell Row",                   "pull",      ["compound"], ["barbell"],                         ["lats", "rear_delt"],  ["biceps", "traps"],                 7),
    _ExTemplate("ROW",              "DUMBBELL_ROW",                  "Dumbbell Row",                  "pull",      ["compound"], ["dumbbell"],                        ["lats", "rear_delt"],  ["biceps", "traps"],                 4),
    _ExTemplate("ROW",              "CABLE_ROW",                     "Cable Row",                     "pull",      ["compound"], ["cable"],                           ["lats", "rear_delt"],  ["biceps", "traps"],                 3),
    _ExTemplate("ROW",              "T_BAR_ROW",                     "T-Bar Row",                     "pull",      ["compound"], ["barbell"],                         ["lats", "rear_delt"],  ["biceps", "traps"],                 7),
    _ExTemplate("ROW",              "SEATED_CABLE_ROW",              "Seated Cable Row",              "pull",      ["compound"], ["cable"],                           ["lats", "rear_delt"],  ["biceps", "traps"],                 3),
    _ExTemplate("ROW",              "FACE_PULL",                     "Face Pull",                     "pull",      ["isolation"], ["cable"],                          ["rear_delt"],           ["traps"],                           3),
    _ExTemplate("ROW",              "INVERTED_ROW",                  "Inverted Row",                  "pull",      ["compound"], ["pullup_bar", "barbell", "smith_machine", "trx", "rings"], ["lats", "rear_delt"], ["biceps"], 5),
    _ExTemplate("HYPEREXTENSION",   "BACK_EXTENSION",                "Back Extension",                "pull",      ["isolation"], ["bench", "machine"],               ["lower_back"],          ["hamstrings", "glutes"],            4),
    # PULL — biceps isolation
    _ExTemplate("CURL",             "BARBELL_CURL",                  "Barbell Curl",                  "arms_bi",   ["isolation"], ["barbell"],                        ["biceps"],              ["forearms"],                        3),
    _ExTemplate("CURL",             "DUMBBELL_CURL",                 "Dumbbell Curl",                 "arms_bi",   ["isolation"], ["dumbbell"],                       ["biceps"],              ["forearms"],                        2),
    _ExTemplate("CURL",             "HAMMER_CURL",                   "Hammer Curl",                   "arms_bi",   ["isolation"], ["dumbbell"],                       ["biceps", "forearms"],  [],                                  2),
    _ExTemplate("CURL",             "PREACHER_CURL",                 "Preacher Curl",                 "arms_bi",   ["isolation"], ["barbell", "dumbbell", "ez_bar"],  ["biceps"],              ["forearms"],                        3),
    _ExTemplate("CURL",             "INCLINE_DUMBBELL_CURL",         "Incline Dumbbell Curl",         "arms_bi",   ["isolation"], ["dumbbell"],                       ["biceps"],              ["forearms"],                        3),
    _ExTemplate("CURL",             "EZ_BAR_CURL",                   "EZ-Bar Curl",                   "arms_bi",   ["isolation"], ["barbell", "ez_bar"],              ["biceps"],              ["forearms"],                        3),

    # -----------------------------------------------------------------------
    # SQUAT — compound
    # -----------------------------------------------------------------------
    _ExTemplate("SQUAT",            "BARBELL_BACK_SQUAT",            "Barbell Back Squat",            "squat",     ["compound"], ["barbell", "smith_machine"],        ["quads", "glutes"],     ["hamstrings", "lower_back"],        8),
    _ExTemplate("SQUAT",            "BARBELL_FRONT_SQUAT",           "Barbell Front Squat",           "squat",     ["compound"], ["barbell"],                         ["quads", "glutes"],     ["hamstrings", "lower_back"],        9),
    _ExTemplate("SQUAT",            "GOBLET_SQUAT",                  "Goblet Squat",                  "squat",     ["compound"], ["dumbbell", "kettlebell", "plate"],  ["quads", "glutes"],     ["hamstrings"],                      3),
    _ExTemplate("SQUAT",            "BOX_SQUAT",                     "Box Squat",                     "squat",     ["compound"], ["box", "barbell"],                  ["quads", "glutes"],     ["hamstrings", "lower_back"],        6),
    _ExTemplate("SQUAT",            "HACK_SQUAT",                    "Hack Squat",                    "squat",     ["compound"], ["machine", "smith_machine"],         ["quads", "glutes"],     ["hamstrings"],                      5),
    _ExTemplate("SQUAT",            "LEG_PRESS",                     "Leg Press",                     "squat",     ["compound"], ["machine"],                         ["quads", "glutes"],     ["hamstrings"],                      4),

    # LUNGE / SPLIT
    _ExTemplate("LUNGE",            "DUMBBELL_LUNGE",                "Dumbbell Lunge",                "lunge",     ["compound"], ["dumbbell"],                        ["quads", "glutes"],     ["hamstrings", "hip_flexors"],       4),
    _ExTemplate("LUNGE",            "WALKING_LUNGE",                 "Walking Lunge",                 "lunge",     ["compound"], ["dumbbell", "barbell", "bodyweight", "weight_vest"], ["quads", "glutes"], ["hamstrings", "hip_flexors"], 4),
    _ExTemplate("LUNGE",            "REVERSE_LUNGE",                 "Reverse Lunge",                 "lunge",     ["compound"], ["dumbbell", "barbell", "bodyweight"], ["quads", "glutes"],   ["hamstrings", "hip_flexors"],       4),
    _ExTemplate("LUNGE",            "BULGARIAN_SPLIT_SQUAT",         "Bulgarian Split Squat",         "lunge",     ["compound"], ["dumbbell", "barbell", "bodyweight"], ["quads", "glutes"],   ["hamstrings", "hip_flexors"],       7),
    _ExTemplate("LUNGE",            "STEP_UP",                       "Step-Up",                       "lunge",     ["compound"], ["bench", "box"],                    ["quads", "glutes"],     ["hamstrings"],                      3),

    # -----------------------------------------------------------------------
    # HINGE — compound
    # -----------------------------------------------------------------------
    _ExTemplate("DEADLIFT",         "BARBELL_DEADLIFT",              "Barbell Deadlift",              "hinge",     ["compound"], ["barbell"],                         ["hamstrings", "glutes"],["lower_back", "traps"],             8),
    _ExTemplate("DEADLIFT",         "ROMANIAN_DEADLIFT",             "Romanian Deadlift",             "hinge",     ["compound"], ["barbell"],                         ["hamstrings", "glutes"],["lower_back"],                      6),
    _ExTemplate("DEADLIFT",         "DUMBBELL_ROMANIAN_DEADLIFT",    "Dumbbell Romanian Deadlift",    "hinge",     ["compound"], ["dumbbell"],                        ["hamstrings", "glutes"],["lower_back"],                      5),
    _ExTemplate("DEADLIFT",         "SUMO_DEADLIFT",                 "Sumo Deadlift",                 "hinge",     ["compound"], ["barbell"],                         ["hamstrings", "glutes"],["adductors", "lower_back"],         7),
    _ExTemplate("DEADLIFT",         "TRAP_BAR_DEADLIFT",             "Trap Bar Deadlift",             "hinge",     ["compound"], ["barbell"],                         ["hamstrings", "glutes", "quads"], ["lower_back", "traps"],   7),
    _ExTemplate("HIP_RAISE",        "BARBELL_HIP_THRUST",            "Barbell Hip Thrust",            "hinge",     ["compound"], ["barbell"],                         ["glutes"],              ["hamstrings"],                      5),
    _ExTemplate("HIP_RAISE",        "DUMBBELL_HIP_THRUST",           "Dumbbell Hip Thrust",           "hinge",     ["compound"], ["dumbbell"],                        ["glutes"],              ["hamstrings"],                      4),
    _ExTemplate("HIP_RAISE",        "GLUTE_BRIDGE",                  "Glute Bridge",                  "hinge",     ["compound"], ["bodyweight", "band", "ankle_weight"], ["glutes"],           ["hamstrings"],                      1),
    _ExTemplate("LEG_CURL",         "LYING_LEG_CURL",                "Lying Leg Curl",                "hinge",     ["isolation"], ["machine"],                        ["hamstrings"],          [],                                  2),
    _ExTemplate("LEG_CURL",         "SEATED_LEG_CURL",               "Seated Leg Curl",               "hinge",     ["isolation"], ["machine"],                        ["hamstrings"],          [],                                  2),
    _ExTemplate("LEG_CURL",         "GOOD_MORNING",                  "Good Morning",                  "hinge",     ["compound"], ["barbell"],                         ["hamstrings", "lower_back"], ["glutes"],                    6),

    # -----------------------------------------------------------------------
    # TRICEPS isolation
    # -----------------------------------------------------------------------
    _ExTemplate("TRICEPS_EXTENSION","TRICEPS_PUSHDOWN",              "Triceps Pushdown",              "arms_tri",  ["isolation"], ["cable"],                          ["triceps"],             [],                                  2),
    _ExTemplate("TRICEPS_EXTENSION","SKULL_CRUSHER",                 "Skull Crusher",                 "arms_tri",  ["isolation"], ["barbell", "dumbbell", "ez_bar"],  ["triceps"],             [],                                  5),
    _ExTemplate("TRICEPS_EXTENSION","OVERHEAD_DUMBBELL_TRICEPS_EXTENSION","Overhead DB Triceps Ext.","arms_tri",  ["isolation"], ["dumbbell"],                        ["triceps"],             [],                                  4),
    _ExTemplate("TRICEPS_EXTENSION","TRICEPS_DIP",                   "Triceps Dip",                   "arms_tri",  ["isolation"], ["bench"],                          ["triceps", "chest"],    ["front_delt"],                      5),

    # -----------------------------------------------------------------------
    # CORE
    # -----------------------------------------------------------------------
    _ExTemplate("PLANK",            "PLANK",                         "Plank",                         "core",      ["core"], ["bodyweight"],                          ["abs", "obliques"],     ["lower_back"],                      2),
    _ExTemplate("PLANK",            "SIDE_PLANK",                    "Side Plank",                    "core",      ["core"], ["bodyweight"],                          ["obliques"],            ["abs", "lower_back"],               3),
    _ExTemplate("CRUNCH",           "CRUNCH",                        "Crunch",                        "core",      ["core"], ["bodyweight"],                          ["abs"],                 ["obliques"],                        1),
    _ExTemplate("CRUNCH",           "BICYCLE_CRUNCH",                "Bicycle Crunch",                "core",      ["core"], ["bodyweight"],                          ["abs", "obliques"],     [],                                  2),
    _ExTemplate("CRUNCH",           "REVERSE_CRUNCH",                "Reverse Crunch",                "core",      ["core"], ["bodyweight"],                          ["abs"],                 ["hip_flexors"],                     3),
    _ExTemplate("LEG_RAISE",        "LYING_LEG_RAISE",               "Lying Leg Raise",               "core",      ["core"], ["bodyweight", "ankle_weight"],          ["abs"],                 ["hip_flexors"],                     3),
    _ExTemplate("LEG_RAISE",        "HANGING_LEG_RAISE",             "Hanging Leg Raise",             "core",      ["core"], ["pullup_bar", "ankle_weight"],          ["abs"],                 ["hip_flexors"],                     6),
    _ExTemplate("LEG_RAISE",        "KNEE_RAISE",                    "Knee Raise",                    "core",      ["core"], ["pullup_bar"],                          ["abs"],                 ["hip_flexors"],                     4),
    _ExTemplate("CORE",             "DEAD_BUG",                      "Dead Bug",                      "core",      ["core"], ["bodyweight"],                          ["abs"],                 ["lower_back"],                      2),
    _ExTemplate("CORE",             "RUSSIAN_TWIST",                 "Russian Twist",                 "core",      ["core"], ["bodyweight", "dumbbell", "medicine_ball", "plate"], ["obliques"], ["abs"],                         3),
    _ExTemplate("CORE",             "KNEELING_AB_WHEEL",             "Kneeling Ab Wheel",             "core",      ["core"], ["ab_wheel"],                            ["abs"],                 ["lower_back", "lats"],              6),
    _ExTemplate("CORE",             "BARBELL_ROLLOUT",               "Barbell Roll-out",              "core",      ["core"], ["ab_wheel", "barbell"],                 ["abs"],                 ["lower_back", "lats"],              8),

    # -----------------------------------------------------------------------
    # TOTAL BODY
    # -----------------------------------------------------------------------
    _ExTemplate("TOTAL_BODY",       "BURPEE",                        "Burpee",                        "total_body",["total_body","compound"],["bodyweight"],           ["quads", "chest"],      ["abs", "front_delt", "hamstrings"], 7),
    _ExTemplate("TOTAL_BODY",       "KETTLEBELL_SWING",              "Kettlebell Swing",              "total_body",["total_body","compound"],["kettlebell"],           ["hamstrings", "glutes"],["abs", "lower_back", "traps"],      5),
    # -----------------------------------------------------------------------
    # CARRY
    # -----------------------------------------------------------------------
    _ExTemplate("CARRY",            "FARMERS_WALK",                  "Farmer's Walk",                 "total_body",["total_body","compound"],["dumbbell","kettlebell","plate","sandbag"], ["traps", "forearms"], ["quads", "abs"], 4),
    _ExTemplate("CARRY",            "OVERHEAD_CARRY",                "Overhead Carry",                "shoulders", ["compound"],           ["dumbbell","kettlebell"],  ["front_delt", "traps"], ["triceps"],                         5),
    # -----------------------------------------------------------------------
    # PLYO
    # -----------------------------------------------------------------------
    _ExTemplate("PLYO",             "BOX_JUMP",                      "Box Jump",                      "total_body",["total_body","compound"],["box"],                  ["quads", "glutes"],     ["hamstrings", "calves"],            8),
    _ExTemplate("PLYO",             "JUMP_SQUAT",                    "Jump Squat",                    "squat",     ["compound"],           ["bodyweight"],              ["quads", "glutes"],     ["hamstrings"],                      7),
    _ExTemplate("PLYO",             "ALTERNATING_JUMP_LUNGE",        "Alternating Jump Lunge",        "lunge",     ["compound"],           ["bodyweight"],              ["quads", "glutes"],     ["hamstrings"],                      8),
    _ExTemplate("PLYO",             "MEDICINE_BALL_SLAM",            "Medicine Ball Slam",            "total_body",["total_body","compound"],["medicine_ball"],         ["abs", "lats"],         ["obliques", "triceps"],             5),
    _ExTemplate("PLYO",             "MEDICINE_BALL_SIDE_THROW",      "Medicine Ball Side Throw",      "core",      ["core","compound"],     ["medicine_ball"],           ["obliques"],            ["abs"],                             5),
    # -----------------------------------------------------------------------
    # BATTLE ROPE
    # -----------------------------------------------------------------------
    _ExTemplate("BATTLE_ROPE",      "ALTERNATING_WAVE",              "Battle Rope Alternating Wave",  "total_body",["total_body"],         ["battle_rope"],             ["front_delt", "biceps"],["abs", "forearms"],                 6),
    _ExTemplate("BATTLE_ROPE",      "ALTERNATING_SQUAT_WAVE",        "Battle Rope Squat Wave",        "total_body",["total_body","compound"],["battle_rope"],           ["quads", "glutes", "front_delt"], ["hamstrings", "biceps"], 7),
    # -----------------------------------------------------------------------
    # SLED
    # -----------------------------------------------------------------------
    _ExTemplate("SLED",             "PUSH",                          "Sled Push",                     "total_body",["total_body","compound"],["sled"],                  ["quads", "glutes", "chest"], ["hamstrings", "front_delt"],   7),
    _ExTemplate("SLED",             "FORWARD_DRAG",                  "Sled Forward Drag",             "total_body",["total_body","compound"],["sled"],                  ["hamstrings", "glutes"],["quads", "lower_back"],             6),
    # -----------------------------------------------------------------------
    # SANDBAG
    # -----------------------------------------------------------------------
    _ExTemplate("SANDBAG",          "BACK_SQUAT",                    "Sandbag Back Squat",            "squat",     ["compound"],           ["sandbag"],                 ["quads", "glutes"],     ["hamstrings", "lower_back"],        6),
    _ExTemplate("SANDBAG",          "LUNGE",                         "Sandbag Lunge",                 "lunge",     ["compound"],           ["sandbag"],                 ["quads", "glutes"],     ["hamstrings"],                      5),
    _ExTemplate("SANDBAG",          "CLEAN_AND_PRESS",               "Sandbag Clean and Press",       "total_body",["total_body","compound"],["sandbag"],               ["quads", "glutes", "front_delt"], ["hamstrings", "traps"],  8),
    _ExTemplate("SANDBAG",          "ROW",                           "Sandbag Row",                   "pull",      ["compound"],           ["sandbag"],                 ["lats", "rear_delt"],   ["biceps"],                          5),
    _ExTemplate("SANDBAG",          "SHOULDERING",                   "Sandbag Shouldering",           "total_body",["total_body","compound"],["sandbag"],               ["quads", "glutes", "lats"], ["hamstrings", "traps"],        8),
    # -----------------------------------------------------------------------
    # SUSPENSION (TRX / rings)
    # -----------------------------------------------------------------------
    _ExTemplate("SUSPENSION",       "ROW",                           "Suspension Row",                "pull",      ["compound"],           ["trx","rings"],             ["lats", "rear_delt"],   ["biceps"],                          5),
    _ExTemplate("SUSPENSION",       "PUSH_UP",                       "Suspension Push-up",            "push",      ["compound"],           ["trx","rings"],             ["chest"],               ["triceps", "front_delt"],           4),
    _ExTemplate("SUSPENSION",       "CURL",                          "Suspension Curl",               "arms_bi",   ["isolation"],          ["trx","rings"],             ["biceps"],              ["forearms"],                        4),
    _ExTemplate("SUSPENSION",       "DIP",                           "Suspension Dip",                "arms_tri",  ["isolation"],          ["trx","rings"],             ["triceps"],             ["chest"],                           6),
    _ExTemplate("SUSPENSION",       "LUNGE",                         "Suspension Lunge",              "lunge",     ["compound"],           ["trx","rings"],             ["quads", "glutes"],     ["hamstrings", "hip_flexors"],       5),
    _ExTemplate("SUSPENSION",       "SQUAT",                         "Suspension Squat",              "squat",     ["compound"],           ["trx","rings"],             ["quads", "glutes"],     ["hamstrings"],                      4),
    _ExTemplate("SUSPENSION",       "PIKE",                          "Suspension Pike",               "core",      ["core"],               ["trx","rings"],             ["abs"],                 ["lower_back"],                      7),
    _ExTemplate("SUSPENSION",       "HAMSTRING_CURL",                "Suspension Hamstring Curl",     "hinge",     ["isolation"],          ["trx"],                     ["hamstrings"],          ["glutes"],                          5),
    _ExTemplate("SUSPENSION",       "PULL_UP",                       "Suspension Pull-up",            "pull",      ["compound"],           ["rings"],                   ["lats"],                ["biceps", "rear_delt"],             8),
    _ExTemplate("SUSPENSION",       "Y_FLY",                         "Suspension Y Fly",              "shoulders", ["isolation"],          ["trx","rings"],             ["rear_delt"],           ["traps"],                           5),
    # -----------------------------------------------------------------------
    # KETTLEBELL — additional
    # -----------------------------------------------------------------------
    _ExTemplate("CORE",             "TURKISH_GET_UP",                "Turkish Get-Up",                "total_body",["compound"],           ["kettlebell"],              ["abs", "glutes", "quads"],["obliques", "lower_back"],        9),
    _ExTemplate("CORE",             "WINDMILL",                      "Windmill",                      "core",      ["core"],               ["kettlebell","dumbbell"],   ["obliques", "lower_back"],["abs"],                           7),
    # -----------------------------------------------------------------------
    # SWISS BALL
    # -----------------------------------------------------------------------
    _ExTemplate("CRUNCH",           "SWISS_BALL_CRUNCH",             "Swiss Ball Crunch",             "core",      ["core"],               ["swiss_ball"],              ["abs"],                 ["obliques"],                        3),
    _ExTemplate("PLANK",            "SWISS_BALL_PLANK",              "Swiss Ball Plank",              "core",      ["core"],               ["swiss_ball"],              ["abs", "obliques"],     ["lower_back"],                      3),
    _ExTemplate("LEG_CURL",         "SWISS_BALL_HIP_RAISE_AND_LEG_CURL", "Swiss Ball Hip Raise & Leg Curl", "hinge", ["isolation"],       ["swiss_ball"],              ["hamstrings", "glutes"],["lower_back"],                      4),
    _ExTemplate("CORE",             "SWISS_BALL_PIKE",               "Swiss Ball Pike",               "core",      ["core"],               ["swiss_ball"],              ["abs"],                 ["lower_back"],                      7),
    _ExTemplate("PUSH_UP",          "SWISS_BALL_PUSH_UP",            "Swiss Ball Push-up",            "push",      ["compound"],           ["swiss_ball"],              ["chest"],               ["triceps", "front_delt"],           3),
    # -----------------------------------------------------------------------
    # BOSU BALL
    # -----------------------------------------------------------------------
    _ExTemplate("SQUAT",            "SPLIT_SQUAT",                   "Split Squat",                   "squat",     ["compound"],           ["bosu_ball", "bodyweight"], ["quads", "glutes"],     ["hamstrings", "hip_flexors"],       4),
    _ExTemplate("PLANK",            "PUSH_UP_POSITION_PLANK",        "Push-Up Position Plank",        "core",      ["core"],               ["bosu_ball", "bodyweight"], ["abs", "obliques"],    ["lower_back"],                      3),
    # -----------------------------------------------------------------------
    # ANKLE WEIGHT
    # -----------------------------------------------------------------------
    _ExTemplate("HIP_RAISE",        "SINGLE_LEG_GLUTE_BRIDGE",       "Single-Leg Glute Bridge",       "hinge",     ["compound"],           ["ankle_weight", "bodyweight"], ["glutes"],          ["hamstrings"],                      3),
    # -----------------------------------------------------------------------
    # ROPE
    # -----------------------------------------------------------------------
    _ExTemplate("LATERAL_RAISE",    "ROPE_CLIMB",                    "Rope Climb",                    "pull",      ["compound"],           ["rope"],                    ["lats", "biceps"],      ["forearms", "rear_delt"],           8),
    # -----------------------------------------------------------------------
    # JUMP ROPE (CARDIO category)
    # -----------------------------------------------------------------------
    _ExTemplate("CARDIO",           "JUMP_ROPE",                     "Jump Rope",                     "total_body",["total_body"],         ["jump_rope"],               ["calves"],              ["quads", "abs"],                    3),
    _ExTemplate("CARDIO",           "JUMP_ROPE_JOG",                 "Jump Rope Jog",                 "total_body",["total_body"],         ["jump_rope"],               ["calves"],              ["quads", "abs"],                    2),
    # -----------------------------------------------------------------------
    # FOAM ROLLER
    # -----------------------------------------------------------------------
    _ExTemplate("HIP_RAISE",        "SINGLE_LEG_HIP_RAISE_WITH_FOOT_ON_FOAM_ROLLER", "Hip Raise on Foam Roller", "hinge", ["core"], ["foam_roller"],             ["glutes", "hamstrings"],["lower_back"],                          3),
    _ExTemplate("CRUNCH",           "THORACIC_CRUNCHES_ON_FOAM_ROLLER", "Thoracic Crunches on Foam Roller", "core", ["core"],          ["foam_roller"],             ["abs"],                 ["lower_back"],                        2),
    # SLIDING_DISC exercises removed pending verification of correct Garmin
    # category/name via Exercises.json (category "SLIDING_DISC" is rejected
    # by the Garmin API with "Invalid category").
]
```

- [ ] **Step 3.5 — Run the test**

```
pytest tests/test_fitness_rank.py::test_all_pool_exercises_have_difficulty -v
```

Expected: **PASS**. Also run the full suite to confirm nothing else broke:

```
pytest tests/ -v
```

- [ ] **Step 3.6 — Commit**

```bash
git add web/workout_generator.py tests/test_fitness_rank.py
git commit -m "feat(generator): add difficulty 1-10 to all pool exercises"
```

---

## Task 4: Health exclusions + rank-band selection in `workout_generator.py`

**Files:**
- Modify: `web/workout_generator.py`

> **Critical**: DB health condition values are `"joint_problems"`, `"back_pain"`, `"heart_condition"`, `"asthma"`, `"high_blood_pressure"`, `"diabetes"` — use these exact strings as exclusion dict keys.

- [ ] **Step 4.1 — Write the failing tests**

Add to `tests/test_fitness_rank.py`:

```python
from web.workout_generator import generate, _HEALTH_EXCLUSIONS, _POOL


def test_health_exclusions_dict_exists():
    assert "joint_problems" in _HEALTH_EXCLUSIONS
    assert "back_pain" in _HEALTH_EXCLUSIONS
    assert "heart_condition" in _HEALTH_EXCLUSIONS


def test_joint_problems_excludes_box_jump():
    excluded = _HEALTH_EXCLUSIONS["joint_problems"]
    assert "BOX_JUMP" in excluded
    assert "JUMP_SQUAT" in excluded
    assert "BURPEE" in excluded


def test_back_pain_excludes_deadlift():
    excluded = _HEALTH_EXCLUSIONS["back_pain"]
    assert "BARBELL_DEADLIFT" in excluded
    assert "GOOD_MORNING" in excluded


def test_generate_with_joint_problems_has_no_box_jump():
    plan = generate(
        equipment=["bodyweight", "box"],
        goal="general_fitness",
        duration_minutes=45,
        health_conditions=["joint_problems"],
        seed=42,
    )
    names = [ex.name for ex in plan.exercises]
    assert "BOX_JUMP" not in names
    assert "JUMP_SQUAT" not in names


def test_generate_with_rank_band_stays_within_range():
    plan = generate(
        equipment=["bodyweight", "dumbbell", "barbell", "cable", "machine"],
        goal="general_fitness",
        duration_minutes=45,
        fitness_rank=3.0,
        seed=42,
    )
    # All exercises must be within rank ± 4 (widest fallback band)
    for ex in plan.exercises:
        pool_ex = next(p for p in _POOL if p.name == ex.name)
        assert abs(pool_ex.difficulty - 3.0) <= 4, (
            f"{ex.name} difficulty {pool_ex.difficulty} too far from rank 3.0"
        )


def test_generate_without_rank_uses_full_pool():
    # Should not raise even without rank
    plan = generate(
        equipment=["bodyweight"],
        goal="general_fitness",
        duration_minutes=45,
        seed=42,
    )
    assert len(plan.exercises) > 0


def test_generate_no_health_conditions_allows_box_jump():
    # Without conditions, high-impact exercises can appear
    # Run many seeds to find a box jump — just ensure it CAN appear
    found = False
    for seed in range(50):
        plan = generate(
            equipment=["bodyweight", "box"],
            goal="general_fitness",
            duration_minutes=45,
            seed=seed,
        )
        if any(ex.name == "BOX_JUMP" for ex in plan.exercises):
            found = True
            break
    assert found, "BOX_JUMP never appeared without health restrictions (check equipment filter)"
```

- [ ] **Step 4.2 — Run to confirm they fail**

```
pytest tests/test_fitness_rank.py::test_health_exclusions_dict_exists -v
```

Expected: `ImportError: cannot import name '_HEALTH_EXCLUSIONS'`

- [ ] **Step 4.3 — Add `_HEALTH_EXCLUSIONS` to `workout_generator.py`**

Add after the `_COMPOUND_TAGS` line (around line 372), before `_available()`:

```python
# ---------------------------------------------------------------------------
# Health-condition exercise exclusions
# Keys match exact DB values stored in User.health_conditions_json
# ---------------------------------------------------------------------------
_HEALTH_EXCLUSIONS: dict[str, set[str]] = {
    "joint_problems": {
        "BOX_JUMP", "JUMP_SQUAT", "BODY_WEIGHT_JUMP_SQUAT",
        "ALTERNATING_JUMP_LUNGE", "DEPTH_JUMP", "LATERAL_PLYO_SQUATS",
        "BURPEE", "PLYOMETRIC_PUSH_UP",
    },
    "back_pain": {
        "BARBELL_DEADLIFT", "SUMO_DEADLIFT", "STIFF_LEG_DEADLIFT",
        "GOOD_MORNING", "BACK_EXTENSION", "REVERSE_HYPEREXTENSION",
    },
    "heart_condition": {
        "BATTLE_ROPE", "ALTERNATING_WAVE", "DOUBLE_ARM_WAVE",
        "BURPEE", "JUMP_SQUAT",
    },
    "asthma": {
        "BATTLE_ROPE", "ALTERNATING_WAVE", "DOUBLE_ARM_WAVE",
    },
    "high_blood_pressure": {
        "BARBELL_DEADLIFT", "BARBELL_BACK_SQUAT", "CLEAN", "POWER_CLEAN",
    },
    "diabetes": set(),  # no movement exclusions
}
```

- [ ] **Step 4.4 — Update `generate()` and `_generate_session()` signatures**

Find the `generate()` function (around line 677) and update its signature and body:

```python
def generate(
    equipment: list[str],
    goal: str,
    duration_minutes: int,
    *,
    fitness_rank: float | None = None,
    health_conditions: list[str] | None = None,
    seed: int | None = None,
) -> WorkoutPlan:
    """Generate a balanced workout.

    Parameters
    ----------
    equipment:
        List of equipment tags from ``EQUIPMENT_OPTIONS``.
    goal:
        One of the ``GOALS`` keys.
    duration_minutes:
        Total session length including warmup/cooldown.
    fitness_rank:
        User's current fitness rank (1.0–10.0). Exercises are biased toward
        this difficulty. When ``None``, the full pool is used.
    health_conditions:
        List of condition strings from User.health_conditions_json.
        Exercises in ``_HEALTH_EXCLUSIONS`` for each condition are removed.
    seed:
        Optional random seed for reproducible generation.
    """
    if goal not in GOALS:
        raise ValueError(f"Unknown goal {goal!r}. Choose from: {list(GOALS)}")

    return _generate_session(
        equipment,
        goal,
        duration_minutes,
        fitness_rank=fitness_rank,
        health_conditions=health_conditions,
        seed=seed,
    )
```

- [ ] **Step 4.5 — Find `_generate_session` and update it**

Search for the `_generate_session` function definition (it calls `_available()` and `_select_exercises()`). Update its signature and add the filtering pipeline:

```python
def _generate_session(
    equipment: list[str],
    goal: str,
    duration_minutes: int,
    *,
    fitness_rank: float | None = None,
    health_conditions: list[str] | None = None,
    seed: int | None = None,
) -> WorkoutPlan:
```

Inside `_generate_session`, find the line that calls `_available(equipment)` and replace the pool-building block with:

```python
    # 1. Filter by equipment
    available = _available(equipment)

    # 2. Apply health-condition hard exclusions
    if health_conditions:
        excluded_names: set[str] = set()
        for condition in health_conditions:
            excluded_names |= _HEALTH_EXCLUSIONS.get(condition, set())
        available = [ex for ex in available if ex.name not in excluded_names]

    # 3. Apply rank band (exercises within ±2 of fitness_rank)
    if fitness_rank is not None:
        for band in (2, 3, 4, None):  # widen until enough exercises
            if band is None:
                band_pool = available  # full pool fallback
            else:
                band_pool = [ex for ex in available if abs(ex.difficulty - fitness_rank) <= band]
            if len(band_pool) >= num:
                available = band_pool
                break
        else:
            available = available  # keep full pool if still short
```

(Note: `num` is computed by `_num_exercises()` before this block — make sure to move the `num = _num_exercises(...)` call above the pool-building block if it isn't already.)

- [ ] **Step 4.6 — Run the tests**

```
pytest tests/test_fitness_rank.py -v
```

Expected: all tests **PASS**.

- [ ] **Step 4.7 — Commit**

```bash
git add web/workout_generator.py tests/test_fitness_rank.py
git commit -m "feat(generator): health-condition exclusions + rank-band exercise selection"
```

---

## Task 5: Wire `fitness_rank` + `health_conditions` into `POST /workout/generate`

**Files:**
- Modify: `web/app.py` (around line 588)

- [ ] **Step 5.1 — Find and update the `workout_generate` route**

In `web/app.py`, find the `workout_generate` route (around line 573). The current `generate()` call is:

```python
plan = generate(equipment=equipment, goal=goal, duration_minutes=duration)
```

Replace it with:

```python
import json as _json  # add at top of function or file if not already imported

# Gather user profile for personalised generation
fitness_rank: float | None = None
health_conditions: list[str] = []
forge_user = get_current_user(request, db)
if forge_user is not None:
    fitness_rank = forge_user.fitness_rank
    health_conditions = _json.loads(forge_user.health_conditions_json or "[]")

plan = generate(
    equipment=equipment,
    goal=goal,
    duration_minutes=duration,
    fitness_rank=fitness_rank,
    health_conditions=health_conditions or None,
)
```

Note: `json` is already imported at the top of `app.py` — check before adding a duplicate import.

- [ ] **Step 5.2 — Run existing tests to confirm nothing broke**

```
pytest tests/ -v
```

Expected: all tests **PASS**.

- [ ] **Step 5.3 — Commit**

```bash
git add web/app.py
git commit -m "feat(app): pass fitness_rank and health_conditions into workout generation"
```

---

## Task 6: `PATCH /my/rank-feedback` endpoint

**Files:**
- Modify: `web/routes_my.py`

- [ ] **Step 6.1 — Write the failing test**

Add to `tests/test_fitness_rank.py`:

```python
from fastapi.testclient import TestClient
from web.app import app
from web.db import get_db
from web.models import User, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _make_client_with_user(fitness_rank: float):
    """Create a test client with a logged-in user at a given rank."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    db = TestingSessionLocal()
    user = User(email="test@example.com", hashed_password="x", fitness_rank=fitness_rank,
                questionnaire_completed=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    user_id = user.id
    db.close()

    client = TestClient(app, raise_server_exceptions=True)
    # Inject session cookie directly
    with client as c:
        with c.session_transaction() as sess:
            sess["user_id"] = user_id
    return client, user_id, TestingSessionLocal


def test_rank_feedback_too_easy_increases_rank():
    client, user_id, SessionLocal = _make_client_with_user(3.0)
    resp = client.patch("/my/rank-feedback", json={
        "trigger": "post_workout",
        "feedback": "too_easy",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["rank_before"] == 3.0
    assert data["rank_after"] == 3.5

    db = SessionLocal()
    user = db.get(User, user_id)
    assert user.fitness_rank == 3.5
    db.close()


def test_rank_feedback_too_hard_decreases_rank():
    client, user_id, SessionLocal = _make_client_with_user(5.0)
    resp = client.patch("/my/rank-feedback", json={
        "trigger": "post_workout",
        "feedback": "too_hard",
    })
    assert resp.status_code == 200
    assert resp.json()["rank_after"] == 4.5


def test_rank_feedback_just_right_no_change():
    client, user_id, SessionLocal = _make_client_with_user(5.0)
    resp = client.patch("/my/rank-feedback", json={
        "trigger": "post_workout",
        "feedback": "just_right",
    })
    assert resp.status_code == 200
    assert resp.json()["rank_after"] == 5.0


def test_rank_feedback_mid_workout_too_easy():
    client, user_id, SessionLocal = _make_client_with_user(5.0)
    resp = client.patch("/my/rank-feedback", json={
        "trigger": "mid_workout",
        "feedback": "too_easy",
    })
    assert resp.status_code == 200
    assert resp.json()["rank_after"] == pytest.approx(5.1)


def test_rank_feedback_clamped_at_10():
    client, user_id, SessionLocal = _make_client_with_user(9.8)
    resp = client.patch("/my/rank-feedback", json={
        "trigger": "post_workout",
        "feedback": "too_easy",
    })
    assert resp.status_code == 200
    assert resp.json()["rank_after"] == 10.0


def test_rank_feedback_clamped_at_1():
    client, user_id, SessionLocal = _make_client_with_user(1.2)
    resp = client.patch("/my/rank-feedback", json={
        "trigger": "post_workout",
        "feedback": "too_hard",
    })
    assert resp.status_code == 200
    assert resp.json()["rank_after"] == 1.0


def test_rank_feedback_mid_just_right_invalid():
    client, _, _ = _make_client_with_user(5.0)
    resp = client.patch("/my/rank-feedback", json={
        "trigger": "mid_workout",
        "feedback": "just_right",
    })
    assert resp.status_code == 400
```

- [ ] **Step 6.2 — Run to confirm they fail**

```
pytest tests/test_fitness_rank.py::test_rank_feedback_too_easy_increases_rank -v
```

Expected: `404 Not Found` — endpoint does not exist yet.

- [ ] **Step 6.3 — Implement the endpoint in `web/routes_my.py`**

Add this import at the top of `web/routes_my.py` (after existing imports):

```python
from pydantic import BaseModel
```

Add this near the imports, after `from web.models import ProgramSession, SavedPlan, WorkoutSession`:

```python
from web.models import ProgramSession, SavedPlan, WorkoutSession, RankFeedback
```

Then add the endpoint after the `log_session` function:

```python
# ---------------------------------------------------------------------------
# Rank feedback
# ---------------------------------------------------------------------------

_RANK_DELTAS: dict[tuple[str, str], float] = {
    ("mid_workout",  "too_easy"):   +0.1,
    ("mid_workout",  "too_hard"):   -0.1,
    ("post_workout", "too_easy"):   +0.5,
    ("post_workout", "just_right"):  0.0,
    ("post_workout", "too_hard"):   -0.5,
}


class RankFeedbackRequest(BaseModel):
    trigger: str    # "mid_workout" | "post_workout"
    feedback: str   # "too_easy" | "just_right" | "too_hard"
    session_id: str | None = None


@router.patch("/rank-feedback")
async def rank_feedback(
    body: RankFeedbackRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _require_user(request, db)
    if user is None:
        return RedirectResponse("/auth/login-forge", status_code=303)

    key = (body.trigger, body.feedback)
    if key not in _RANK_DELTAS:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid trigger/feedback combination: {key}")

    delta = _RANK_DELTAS[key]
    rank_before = user.fitness_rank if user.fitness_rank is not None else 3.0
    rank_after = max(1.0, min(10.0, rank_before + delta))

    user.fitness_rank = rank_after  # type: ignore[assignment]

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
    db.commit()

    return {"rank_before": rank_before, "rank_after": rank_after}
```

- [ ] **Step 6.4 — Run the tests**

```
pytest tests/test_fitness_rank.py -k "rank_feedback" -v
```

Expected: all 7 feedback tests **PASS**.

- [ ] **Step 6.5 — Run the full test suite**

```
pytest tests/ -v
```

Expected: all tests **PASS**.

- [ ] **Step 6.6 — Commit**

```bash
git add web/routes_my.py tests/test_fitness_rank.py
git commit -m "feat(routes): PATCH /my/rank-feedback endpoint with delta table and RankFeedback logging"
```

---

## Task 7: Questionnaire fitness level descriptions

**Files:**
- Modify: `web/routes_onboarding.py`
- Modify: `web/templates/questionnaire.html`
- Modify: `web/translations.py`

- [ ] **Step 7.1 — Add description translation keys to `translations.py`**

In `web/translations.py`, find the English `fitness_beginner` / `fitness_intermediate` / `fitness_advanced` keys (around line 333) and add three description keys below them:

```python
        "fitness_beginner":         "Beginner",
        "fitness_intermediate":     "Intermediate",
        "fitness_advanced":         "Advanced",
        "fitness_beginner_desc":    "New to exercise, or returning after a long break. Working out less than 2× / week.",
        "fitness_intermediate_desc":"Working out regularly, 2–4× / week for at least 6 months.",
        "fitness_advanced_desc":    "Training consistently 4+ times per week. Comfortable with compound lifts and free weights.",
```

Do the same in the Hebrew block (around line 724), using the same English text (acceptable to leave English for description strings in Hebrew since these are detailed descriptions):

```python
        "fitness_beginner":         "מתחיל",
        "fitness_intermediate":     "בינוני",
        "fitness_advanced":         "מתקדם",
        "fitness_beginner_desc":    "New to exercise, or returning after a long break. Working out less than 2× / week.",
        "fitness_intermediate_desc":"Working out regularly, 2–4× / week for at least 6 months.",
        "fitness_advanced_desc":    "Training consistently 4+ times per week. Comfortable with compound lifts and free weights.",
```

- [ ] **Step 7.2 — Add `desc` key to `FITNESS_LEVELS` in `routes_onboarding.py`**

Find the `FITNESS_LEVELS` list (around line 58):

```python
FITNESS_LEVELS = [
    {"value": "Beginner",     "label": "fitness_beginner",     "desc": "fitness_beginner_desc"},
    {"value": "Intermediate", "label": "fitness_intermediate", "desc": "fitness_intermediate_desc"},
    {"value": "Advanced",     "label": "fitness_advanced",     "desc": "fitness_advanced_desc"},
]
```

- [ ] **Step 7.3 — Update the questionnaire template to render descriptions**

In `web/templates/questionnaire.html`, find the fitness level options block (around line 222):

```html
      <div class="wopts wopts--row">
        {% for lvl in fitness_levels %}
        <label class="wopt">
          <input type="radio" name="fitness_level_pick" value="{{ lvl.value }}"
            {% if lvl.value == existing_fitness_level %}checked{% endif %}>
          {{ t(lvl.label) }}
        </label>
        {% endfor %}
      </div>
```

Replace with:

```html
      <div class="wopts wopts--col">
        {% for lvl in fitness_levels %}
        <label class="wopt wopt--with-desc">
          <input type="radio" name="fitness_level_pick" value="{{ lvl.value }}"
            {% if lvl.value == existing_fitness_level %}checked{% endif %}>
          <span class="wopt-title">{{ t(lvl.label) }}</span>
          <span class="wopt-desc">{{ t(lvl.desc) }}</span>
        </label>
        {% endfor %}
      </div>
```

Add the CSS for `wopt--with-desc`, `wopt-title`, `wopt-desc` in the questionnaire's `<style>` block (or in `base.html` global styles). Add near existing `.wopt` styles:

```css
.wopt--with-desc { flex-direction: column; align-items: flex-start; gap: 2px; padding: 10px 14px; }
.wopt-title      { font-weight: 600; font-size: 14px; }
.wopt-desc       { font-size: 12px; color: var(--text-secondary, #888); line-height: 1.4; }
```

- [ ] **Step 7.4 — Commit**

```bash
git add web/routes_onboarding.py web/templates/questionnaire.html web/translations.py
git commit -m "feat(questionnaire): add one-line descriptions to fitness level options"
```

---

## Task 8: Mid-workout feedback buttons in the player

**Files:**
- Modify: `web/templates/workout_preview.html`

The workout player is the Bootstrap fullscreen modal `#workoutPlayerModal`. The control buttons are at the bottom of the modal body (Pause and Skip). We add a "Too easy / Too hard" button pair that:
1. Scales reps of remaining exercise steps in `playerQueue` by ×1.2 or ×0.8
2. Calls `PATCH /my/rank-feedback` with `trigger: "mid_workout"`
3. Disables itself for the rest of the session after one tap

- [ ] **Step 8.1 — Add the HTML for mid-workout buttons**

In `web/templates/workout_preview.html`, find the player controls `<div>` (around line 358):

```html
        <div class="d-flex gap-3 mt-2">
          <button type="button" class="btn btn-outline-light px-4 py-2 fw-semibold"
                  id="playerPauseBtn">
            ...
          </button>
          <button type="button" class="btn btn-outline-secondary px-4 py-2" id="playerSkipBtn">
            ...
          </button>
        </div>
```

After that closing `</div>`, add:

```html
        {# Mid-workout difficulty feedback #}
        <div class="d-flex gap-2 mt-1" id="midWorkoutFeedback" style="opacity:.6;">
          <button type="button" class="btn btn-sm btn-outline-warning px-3" id="midTooEasyBtn">
            <i class="bi bi-chevron-double-up me-1"></i>Too easy
          </button>
          <button type="button" class="btn btn-sm btn-outline-danger px-3" id="midTooHardBtn">
            <i class="bi bi-chevron-double-down me-1"></i>Too hard
          </button>
        </div>
```

- [ ] **Step 8.2 — Add the JS for mid-workout feedback**

In the player JS section of `workout_preview.html` (inside the IIFE, after the `playerSkipBtn` click handler around line 1234), add:

```javascript
// ── Mid-workout difficulty feedback ──────────────────────────────────
let midFeedbackUsed = false;

function applyMidWorkoutRepScale(factor) {
  if (midFeedbackUsed) return;
  midFeedbackUsed = true;

  // Disable both buttons
  document.getElementById('midTooEasyBtn').disabled = true;
  document.getElementById('midTooHardBtn').disabled = true;
  document.getElementById('midWorkoutFeedback').style.opacity = '0.3';

  // Scale reps for all remaining exercise steps (from playerIndex+1 onward)
  for (let i = playerIndex + 1; i < playerQueue.length; i++) {
    const step = playerQueue[i];
    if (step.type === 'exercise' && step.ex.reps) {
      step.ex.reps = Math.max(1, Math.round(step.ex.reps * factor));
    }
  }

  // Also adjust current exercise if it's rep-based and not yet started
  const current = playerQueue[playerIndex];
  if (current && current.type === 'exercise' && current.ex.reps && playerTimeLeft === 0) {
    current.ex.reps = Math.max(1, Math.round(current.ex.reps * factor));
    renderPlayerStep();
  }

  // Notify server (fire-and-forget)
  fetch('/my/rank-feedback', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      trigger: 'mid_workout',
      feedback: factor > 1 ? 'too_easy' : 'too_hard',
    }),
  }).catch(() => {}); // ignore network errors silently
}

document.getElementById('midTooEasyBtn').addEventListener('click', () => applyMidWorkoutRepScale(1.2));
document.getElementById('midTooHardBtn').addEventListener('click', () => applyMidWorkoutRepScale(0.8));
```

- [ ] **Step 8.3 — Reset `midFeedbackUsed` when the player opens**

Find the line where `playerStartStep()` is called to begin the workout (around line 1261). Add `midFeedbackUsed = false;` and re-enable the buttons just before it:

```javascript
  midFeedbackUsed = false;
  document.getElementById('midTooEasyBtn').disabled = false;
  document.getElementById('midTooHardBtn').disabled = false;
  document.getElementById('midWorkoutFeedback').style.opacity = '0.6';
  playerStartStep();
```

- [ ] **Step 8.4 — Commit**

```bash
git add web/templates/workout_preview.html
git commit -m "feat(player): add mid-workout too easy/too hard buttons with rep scaling"
```

---

## Task 9: Post-workout feedback prompt in the player finish screen

**Files:**
- Modify: `web/templates/workout_preview.html`

When `step.type === 'complete'` renders, show a 3-button prompt. The buttons call `PATCH /my/rank-feedback` with `trigger: "post_workout"` then dismiss the modal.

- [ ] **Step 9.1 — Add the post-workout feedback HTML to the player modal**

In `web/templates/workout_preview.html`, inside the player modal body, after the progress bar `</div>` (around line 356) add a hidden post-workout panel:

```html
        {# Post-workout feedback — shown only on the complete step #}
        <div id="postWorkoutFeedback" class="text-center" style="display:none;">
          <p class="text-muted mb-3" style="font-size:.9rem;">How did that feel?</p>
          <div class="d-flex gap-2 justify-content-center flex-wrap">
            <button type="button" class="btn btn-outline-warning px-4" id="postTooEasyBtn">
              <i class="bi bi-emoji-laughing me-1"></i>Too easy
            </button>
            <button type="button" class="btn btn-outline-success px-4" id="postJustRightBtn">
              <i class="bi bi-emoji-smile me-1"></i>Just right
            </button>
            <button type="button" class="btn btn-outline-danger px-4" id="postTooHardBtn">
              <i class="bi bi-emoji-frown me-1"></i>Too hard
            </button>
          </div>
        </div>
```

- [ ] **Step 9.2 — Show the panel on the complete step**

In `renderPlayerStep()`, in the `else if (step.type === 'complete')` block (around line 1133), add:

```javascript
    document.getElementById('postWorkoutFeedback').style.display = 'block';
    document.getElementById('midWorkoutFeedback').style.display  = 'none';
```

- [ ] **Step 9.3 — Add JS for post-workout feedback buttons**

After the mid-workout JS added in Task 8, add:

```javascript
// ── Post-workout feedback ─────────────────────────────────────────────
function submitPostWorkoutFeedback(feedback) {
  // Disable all three buttons immediately to prevent double-tap
  ['postTooEasyBtn', 'postJustRightBtn', 'postTooHardBtn'].forEach(id => {
    document.getElementById(id).disabled = true;
  });

  fetch('/my/rank-feedback', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ trigger: 'post_workout', feedback }),
  })
  .catch(() => {})
  .finally(() => {
    bootstrap.Modal.getOrCreateInstance(
      document.getElementById('workoutPlayerModal')
    ).hide();
  });
}

document.getElementById('postTooEasyBtn').addEventListener('click',  () => submitPostWorkoutFeedback('too_easy'));
document.getElementById('postJustRightBtn').addEventListener('click', () => submitPostWorkoutFeedback('just_right'));
document.getElementById('postTooHardBtn').addEventListener('click',  () => submitPostWorkoutFeedback('too_hard'));
```

- [ ] **Step 9.4 — Hide the post-workout panel when the player resets**

In the `hide.bs.modal` handler (around line 1238), add:

```javascript
  document.getElementById('postWorkoutFeedback').style.display = 'none';
  document.getElementById('midWorkoutFeedback').style.display  = 'flex';
```

- [ ] **Step 9.5 — Commit**

```bash
git add web/templates/workout_preview.html
git commit -m "feat(player): add post-workout too-easy/just-right/too-hard feedback prompt"
```

---

## Task 10: Feedback prompt on the progress page for skipped sessions

**Files:**
- Modify: `web/routes_my.py` (update `my_progress` query)
- Modify: `web/templates/my_progress.html`

Show the 3-button prompt inline on any session row that has no `RankFeedback` with `trigger="post_workout"` in the DB.

- [ ] **Step 10.1 — Update `my_progress` route to include feedback state**

In `web/routes_my.py`, update the `my_progress` handler:

```python
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

    # Build set of session IDs that already have post_workout feedback
    from web.models import RankFeedback
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
```

- [ ] **Step 10.2 — Add the inline feedback row to the sessions table**

In `web/templates/my_progress.html`, find the table row for each session (around line 103). After the `</tr>` that closes each session row, add a conditional feedback row:

```html
          {% if s.id not in rated_session_ids %}
          <tr id="feedback-row-{{ s.id }}">
            <td colspan="5" style="padding:4px 20px 12px;">
              <div class="d-flex align-items-center gap-2 flex-wrap">
                <span style="font-size:12px;color:var(--text-muted);">How did it feel?</span>
                <button class="btn btn-sm btn-outline-warning py-0 px-2"
                        onclick="submitProgressFeedback('{{ s.id }}','too_easy',this)">Too easy</button>
                <button class="btn btn-sm btn-outline-success py-0 px-2"
                        onclick="submitProgressFeedback('{{ s.id }}','just_right',this)">Just right</button>
                <button class="btn btn-sm btn-outline-danger py-0 px-2"
                        onclick="submitProgressFeedback('{{ s.id }}','too_hard',this)">Too hard</button>
              </div>
            </td>
          </tr>
          {% endif %}
```

- [ ] **Step 10.3 — Add the JS for progress page feedback**

Add a `<script>` block at the bottom of `my_progress.html` (before `{% endblock %}`):

```html
<script>
function submitProgressFeedback(sessionId, feedback, btn) {
  // Disable all buttons in this row immediately
  const row = document.getElementById('feedback-row-' + sessionId);
  row.querySelectorAll('button').forEach(b => b.disabled = true);

  fetch('/my/rank-feedback', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ trigger: 'post_workout', feedback, session_id: sessionId }),
  })
  .then(() => { row.style.display = 'none'; })
  .catch(() => { row.querySelectorAll('button').forEach(b => b.disabled = false); });
}
</script>
```

- [ ] **Step 10.4 — Run full test suite**

```
pytest tests/ -v
```

Expected: all tests **PASS**.

- [ ] **Step 10.5 — Commit**

```bash
git add web/routes_my.py web/templates/my_progress.html
git commit -m "feat(progress): inline post-workout feedback prompt for unrated sessions"
```

---

## Task 11: Run the migration and smoke-test the full flow

- [ ] **Step 11.1 — Apply the migration**

```bash
alembic upgrade head
```

Expected: `Running upgrade 0004 -> 0005, add fitness_rank to users and rank_feedbacks table`

- [ ] **Step 11.2 — Start the dev server and verify the questionnaire**

```bash
python run.py --reload
```

Open `http://127.0.0.1:8000/onboarding` in a browser. Navigate to the fitness level step (step 3). Confirm:
- Each option shows the level name + a one-line description below it
- Selecting a level and completing the questionnaire stores `fitness_rank` in the DB

- [ ] **Step 11.3 — Verify workout generation uses rank**

As a logged-in user with questionnaire complete, go to the dashboard, generate a workout. Confirm in server logs (or a quick `ruff check` smoke) that no exceptions fire. A rank-3 user should not see Barbell Deadlifts (difficulty 8) unless the pool was exhausted.

- [ ] **Step 11.4 — Verify mid-workout buttons**

Generate a workout, open the player modal. Confirm:
- "Too easy" and "Too hard" buttons appear below Pause/Skip
- Tapping "Too easy" changes rep counts for upcoming exercises (observe in the player step display)
- Both buttons become disabled after one tap

- [ ] **Step 11.5 — Verify post-workout prompt**

Complete the workout (skip to the last step). Confirm:
- "How did that feel?" panel with 3 buttons appears
- Tapping "Too easy" closes the modal
- The user's `fitness_rank` in the DB has increased by 0.5

- [ ] **Step 11.6 — Verify progress page prompt**

Go to `/my/progress`. Find a session that was just completed. Confirm an inline "How did it feel?" row appears below it. Tap "Just right" — the row disappears and the rank stays unchanged.

- [ ] **Step 11.7 — Final commit**

```bash
git add -A
git commit -m "chore: verify full fitness rank + health filtering flow"
```

---

## Self-Review Against Spec

| Spec section | Covered by task |
|---|---|
| `User.fitness_rank` float column | Task 1 |
| `RankFeedback` model | Task 1 |
| Alembic migration | Task 1 |
| Initial rank formula from questionnaire | Task 2 |
| `difficulty` on all pool exercises | Task 3 |
| `_HEALTH_EXCLUSIONS` dict | Task 4 |
| Rank-band selection with widening fallback | Task 4 |
| `generate()` new params | Task 4 |
| Wire params into `/workout/generate` route | Task 5 |
| `PATCH /my/rank-feedback` endpoint | Task 6 |
| Delta table (all 5 trigger/feedback combos) | Task 6 |
| `just_right` invalid for `mid_workout` → 400 | Task 6 |
| Questionnaire fitness level descriptions | Task 7 |
| Mid-workout buttons with rep scaling | Task 8 |
| Post-workout prompt in player finish | Task 9 |
| Progress page missed-feedback prompt | Task 10 |
