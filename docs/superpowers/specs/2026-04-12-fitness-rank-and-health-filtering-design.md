# Fitness Rank & Health-Condition Filtering — Design Spec

**Date:** 2026-04-12  
**Status:** Approved  

---

## Overview

Two complementary features shipped together:

1. **Dynamic Fitness Rank (1–10)**: each user has a floating-point rank that starts from their
   questionnaire answers and self-corrects after every workout via "too easy / just right / too
   hard" feedback — both mid-workout and post-workout.
2. **Health-Condition Exercise Filtering**: a hard exclusion map removes unsafe exercises from the
   pool before any rank-based selection occurs.

Together these replace the need for static age/fitness-level rules: a 50+ beginner starts at rank
~1.5, feels their workouts are too easy, taps "too easy" a few times, and naturally climbs toward
harder exercises without any special-case logic.

---

## 1. Data Model

### `User.fitness_rank` (new column)

```python
fitness_rank: Mapped[float | None] = mapped_column(Float, nullable=True)
# Range: 1.0–10.0. Null until questionnaire is completed.
```

Requires an Alembic migration (`alembic revision --autogenerate`).

### Initial rank formula

Computed once when the questionnaire is saved (on `POST /onboarding/questionnaire`):

```python
FITNESS_LEVEL_BASE = {"beginner": 2.0, "intermediate": 5.0, "advanced": 8.0}

base           = FITNESS_LEVEL_BASE.get(fitness_level, 3.0)
age_penalty    = -1.0 if age_range == "50+" else 0.0
health_penalty = -0.5 if health_conditions else 0.0
fitness_rank   = max(1.0, min(10.0, base + age_penalty + health_penalty))
```

### `RankFeedback` (new table, optional analytics)

```python
class RankFeedback(Base):
    __tablename__ = "rank_feedbacks"
    id:           str      # UUID PK
    user_id:      str      # FK → users
    session_id:   str      # FK → workout_sessions (nullable)
    trigger:      str      # "mid_workout" | "post_workout"
    feedback:     str      # "too_easy" | "just_right" | "too_hard"
    delta:        float    # +0.1, 0, -0.1, +0.5, -0.5
    rank_before:  float
    rank_after:   float
    created_at:   datetime
```

---

## 2. Exercise Difficulty Scores

### `_ExTemplate` change

Add `difficulty: int` as the last field (1–10). All existing fields stay in the same position;
the new field is appended with a default-free positional slot — every entry in `_POOL` must supply
it.

```python
@dataclass
class _ExTemplate:
    category:          str
    name:              str
    label:             str
    muscle_group:      str
    tags:              list[str]
    equipment:         list[str]
    primary_muscles:   list[str]
    secondary_muscles: list[str]
    difficulty:        int        # 1–10  ← NEW
```

### Difficulty scoring guide

| Score | Description | Example exercises |
|-------|-------------|-------------------|
| 1–2   | Beginner-accessible, low coordination demand | Push-Up, Dumbbell Curl, Glute Bridge, Plank, Seated Leg Curl |
| 3–4   | Light technique required, stable movements | Goblet Squat, Dumbbell Row, Lat Pulldown, Step-Up, Cable Row |
| 5–6   | Moderate load / technique | Barbell Bench Press, Romanian Deadlift, Pull-Up, Bulgarian Split Squat |
| 7–8   | Advanced technique or high load | Barbell Back Squat, Barbell Deadlift, Weighted Pull-Up, Box Jump |
| 9–10  | Elite / Olympic / extreme plyometric | Power Clean, Clean and Jerk, Snatch, Depth Jump |

All ~150 pool entries are annotated according to this guide.

---

## 3. Health-Condition Hard Exclusions

Applied **before** rank-band filtering. Exercises in the exclusion set are removed from the
available pool unconditionally when the user has the corresponding condition.

```python
_HEALTH_EXCLUSIONS: dict[str, set[str]] = {
    "joints": {
        "BOX_JUMP", "JUMP_SQUAT", "BODY_WEIGHT_JUMP_SQUAT",
        "ALTERNATING_JUMP_LUNGE", "DEPTH_JUMP", "LATERAL_PLYO_SQUATS",
        "BURPEE", "PLYOMETRIC_PUSH_UP",
    },
    "back": {
        "BARBELL_DEADLIFT", "SUMO_DEADLIFT", "STIFF_LEG_DEADLIFT",
        "GOOD_MORNING", "BACK_EXTENSION", "REVERSE_HYPEREXTENSION",
    },
    "heart": {
        "BATTLE_ROPE", "ALTERNATING_WAVE", "DOUBLE_ARM_WAVE",
        "BURPEE", "JUMP_SQUAT",
    },
    "asthma": {
        "BATTLE_ROPE", "ALTERNATING_WAVE", "DOUBLE_ARM_WAVE",
    },
    "hypertension": {
        "BARBELL_DEADLIFT", "BARBELL_BACK_SQUAT", "CLEAN", "POWER_CLEAN",
    },
    "diabetes": set(),  # no movement exclusions; rank is nudged lower at init
}
```

---

## 4. Exercise Selection Changes

### `generate()` new signature

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
```

Both new params are optional — all existing callers (tests, editor routes) continue to work
unchanged.

### Selection pipeline

1. `_available(equipment)` — filter pool by equipment (existing)
2. Apply `_HEALTH_EXCLUSIONS` — remove unsafe exercises
3. Apply rank band — keep exercises where `abs(ex.difficulty - rank) <= 2`
   - If fewer than `num` exercises remain, widen band: ±3 → ±4 → full pool
   - If `fitness_rank` is `None`, skip band filtering (full pool, existing behavior)
4. `_select_exercises(filtered_pool, num, goal)` — existing muscle-group balancing (unchanged)

---

## 5. Rank Progression API

### Endpoint

```
PATCH /my/rank-feedback
```

**Request body:**
```json
{
  "session_id": "optional-uuid",
  "trigger": "mid_workout" | "post_workout",
  "feedback": "too_easy" | "just_right" | "too_hard"
}
```

**Delta table:**

| trigger        | feedback    | Δ rank |
|----------------|-------------|--------|
| mid_workout    | too_easy    | +0.1   |
| mid_workout    | too_hard    | −0.1   |
| post_workout   | too_easy    | +0.5   |
| post_workout   | just_right  | 0      |
| post_workout   | too_hard    | −0.5   |

Note: `just_right` is only valid for `post_workout`. The endpoint returns 400 if
`trigger=mid_workout` and `feedback=just_right`.

Rank is clamped to `[1.0, 10.0]` after applying the delta. A `RankFeedback` row is inserted.

**Response:**
```json
{ "rank_before": 3.5, "rank_after": 4.0 }
```

---

## 6. Mid-Workout Feedback (Player)

The workout player frontend adds a persistent "Too easy / Too hard" button pair visible during
each exercise.

When tapped:
1. All **remaining** exercises in the session have their `reps` scaled:
   - "Too easy" → `reps = round(current_reps × 1.2)`
   - "Too hard" → `reps = round(current_reps × 0.8)`
   - Minimum 1 rep enforced.
2. `PATCH /my/rank-feedback` is called with `trigger: "mid_workout"` and the corresponding
   feedback value → rank shifts ±0.1.
3. Buttons are disabled for the rest of the session after one tap (prevent double-adjusting).

Rep scaling is local to the current session only — it does not modify the saved `WorkoutPlan` or
the already-uploaded Garmin workout.

---

## 7. Post-Workout Feedback (Player + Progress Page)

### Player finish screen

After completing all rounds, the player shows:
```
How did that feel?
[ Too easy ]  [ Just right ]  [ Too hard ]
```
Tapping any button calls `PATCH /my/rank-feedback` with `trigger: "post_workout"`.

### Progress page

Sessions without a `post_workout` rank feedback entry show a small inline prompt:
```
How did this workout feel? [ Too easy ]  [ Just right ]  [ Too hard ]
```
This allows users who skipped the player prompt to still submit feedback.

---

## 8. Questionnaire Fitness Level Descriptions

The `fitness_level` question in the questionnaire is updated with one-line descriptors to help
users self-assess accurately:

| Option | Description shown |
|--------|-------------------|
| Beginner | New to exercise, or returning after a long break. Working out less than 2× / week. |
| Intermediate | Working out regularly, 2–4× / week for at least 6 months. |
| Advanced | Training consistently 4+ times per week. Comfortable with compound lifts and free weights. |

---

## 9. Files Changed

| File | Change |
|------|--------|
| `web/models.py` | Add `User.fitness_rank: float`, add `RankFeedback` model |
| `alembic/versions/xxxx_add_fitness_rank.py` | New migration |
| `web/workout_generator.py` | `_ExTemplate.difficulty`, `_POOL` annotations, `_HEALTH_EXCLUSIONS`, updated `_select_exercises`, updated `generate()` |
| `web/routes_my.py` | `PATCH /my/rank-feedback` endpoint |
| `web/app.py` | Pass `fitness_rank` + `health_conditions` from user to `generate()` in `POST /generate` |
| Questionnaire template | Add fitness level descriptions |
| Workout player JS | Mid-workout buttons + rep scaling + API call |
| Player finish screen | Post-workout 3-button prompt |
| `web/templates/my_progress.html` | Inline feedback prompt for sessions missing post-workout feedback |

---

## 10. Out of Scope

- Rank displayed visibly to the user (could be a future "Level X" badge)
- Rank decay over time (inactivity)
- Per-muscle-group difficulty (all exercises have a single difficulty score)
