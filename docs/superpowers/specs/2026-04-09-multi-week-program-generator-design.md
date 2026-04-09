# Multi-week Program Generator — Design Spec

**Date:** 2026-04-09
**Initiative:** SLOW_BURNS.md — Initiative 2
**Status:** Approved

---

## Problem

Initiative 1 added `Program` + `ProgramSession` models and CRUD routes, but no sessions are ever generated. The detail page shows "No training sessions generated yet." Users have no way to create a full multi-week periodized program.

## Goals

- Generate a complete multi-week periodized training program (all sessions, all Garmin payloads) in one call
- Wizard UI with preview-before-save: user sees the full program before anything is written to DB
- Support linear, undulating (DUP), and block periodization
- Pre-fill from user profile; editable in the wizard

---

## Architecture

### New module: `web/program_generator.py`

Owns all multi-week logic. Calls into `workout_generator._generate_session()` (a refactored internal helper) for per-session generation.

**Key dataclasses:**

```python
@dataclass
class SessionPlan:
    week_num: int
    day_num: int
    focus: str              # "Upper Body — Push"
    workout_name: str       # "Week 2 Day 1 · Push — 45 min"
    exercises: list[ExerciseInfo]
    garmin_payload: dict[str, Any]

@dataclass
class ProgramPlan:
    name: str
    goal: str
    goal_label: str
    periodization_type: str
    duration_weeks: int
    equipment: list[str]
    sessions: list[SessionPlan]
```

**Main function:**

```python
def generate_program(
    goal: str,
    equipment: list[str],
    duration_weeks: int,         # 4 | 6 | 8
    weekly_workout_days: int,    # 2 | 3 | 4 | 5
    duration_minutes: int,       # 30 | 45 | 60
    periodization_type: str,     # "linear" | "undulating" | "block"
    fitness_level: str,          # "beginner" | "intermediate" | "advanced"
    seed: int | None = None,
) -> ProgramPlan
```

### Refactor: `web/workout_generator.py`

Extract `_generate_session()` internal helper with `muscle_groups`, `override_sets`, `override_reps`, `override_rest` parameters. `generate()` continues to call it with `None` overrides — no behavior change. `_available()` gains an optional `muscle_groups` pre-filter.

---

## Periodization Logic

### Linear

Phase boundaries are derived from `duration_weeks`:

| Phase | 4-wk | 6-wk | 8-wk | Sets | Reps | Rest |
|-------|------|------|------|------|------|------|
| Accumulation | 1–2 | 1–2 | 1–3 | 3 | 12–15 | 60s |
| Deload | — | 3 | 4 | 2 | 12–15 | 60s |
| Intensification | 3 | 4–5 | 5–7 | 4 | 6–10 | 90s |
| Peak | 4 | 6 | 8 | 5 | 3–5 | 120s |

### Undulating (DUP)

Rep range rotates by `day_slot mod 3`, same pattern every week:

| Day slot mod 3 | Type | Sets | Reps | Rest |
|---------------|------|------|------|------|
| 0 | Strength | 5 | 3–5 | 120s |
| 1 | Hypertrophy | 4 | 8–12 | 90s |
| 2 | Endurance | 3 | 12–15 | 60s |

### Block

Hard week boundaries, deload between blocks when N ≥ 6:

| Block | Weeks | Sets | Reps | Rest |
|-------|-------|------|------|------|
| Accumulation | 1–⌊N/3⌋ | 3 | 12–15 | 60s |
| Deload (if N≥6) | ⌊N/3⌋+1 | 2 | 12–15 | 60s |
| Intensification | next ⌊N/3⌋ | 4 | 6–10 | 90s |
| Realization | final | 5 | 3–5 | 120s |

---

## Split Patterns

| Days/week | Session sequence |
|-----------|-----------------|
| 2 | Full Body A (push+pull+squat+core), Full Body B (push+pull+hinge+core) |
| 3 | Upper Body—Push, Upper Body—Pull, Lower Body |
| 4 | Upper Push, Lower Body, Upper Pull, Lower Body |
| 5 | Push, Pull, Legs, Upper Body, Lower Body |

Sequence cycles across all weeks. Exercise selection within each session is random (seeded deterministically per week+day).

---

## Routes

| Method | Path | Action |
|--------|------|--------|
| `GET` | `/my/programs/new` | Render wizard with profile pre-fills |
| `POST` | `/my/programs/preview` | Run `generate_program()`, return `ProgramPlan` JSON — no DB write |
| `POST` | `/my/programs` | Extended: accepts `sessions_json`, creates `Program` + all `ProgramSession` rows atomically |

---

## Wizard UI (`/my/programs/new`)

**State 1 — Form:** Goal, Equipment, Duration (4/6/8 wks), Periodization (Linear/Undulating/Block), Days/week (2–5), Session duration (30/45/60 min), Fitness level. All pre-filled from profile. "Preview Program →" triggers fetch to `/my/programs/preview`.

**State 2 — Preview:** Editable program name + scrollable week grid (rows = weeks, columns = days). Each cell shows focus label + top 3 exercises; click to expand. "← Back" restores form. "Save Program" writes to DB and redirects to detail page.

---

## Navigation Updates

- `my_programs.html`: Update "+ Generate New" button href to `/my/programs/new`
- Add "+ New Program" button to header (not just empty state)
