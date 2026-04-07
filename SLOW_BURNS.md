# GarminForge Slow Burns

Strategic, high-effort initiatives that provide substantial long-term value.
Each initiative requires meaningful architectural work, but they build on each other in a clear
dependency chain toward the primary differentiation goal: **multi-week periodized programming**.

---

## The Vision

Today, GarminForge generates a single workout session. The vision is to generate a full
**8-week periodized program**, schedule every session to the Garmin calendar automatically,
track progressive overload session-by-session, and adapt the program based on the user's
actual Garmin device data (recovery, fitness metrics, activity history).

This is what a personal coach provides. No fitness app does it well today.

---

## Dependency Graph

```
Initiative 1 (Program Data Model)  ← start here; nothing else is possible without this
    ├── Initiative 2 (Program Generator)
    │       ├── Initiative 3 (Calendar Batch Scheduling)
    │       └── Initiative 7 (Program Library)
    └── Initiative 4 (Progressive Overload Engine)
            └── Initiative 5 (Garmin Activity Sync)
                    └── Initiative 6 (Adaptive Difficulty)

Initiative 8 (Running + Strength Hybrid) ← requires Initiative 2 + 3
```

---

## Initiative 1: Program Data Model & Storage

**Priority:** Critical (prerequisite for everything else)
**Effort:** 1–2 weeks
**Risk:** Low

### Current state
The database has `SavedPlan` (a single session) and `WorkoutSession` (a log entry), but no concept
of a multi-session program. There is no way to represent "Week 3 Day 2 of an 8-week program."

### The vision
A `Program` groups N `ProgramSession` rows across M weeks, with periodization metadata attached.

### New data models

```python
class Program(Base):
    id: str                  # UUID
    user_id: str             # FK → User
    name: str                # "8-Week Strength Builder"
    goal: str                # Same keys as GOALS dict
    periodization_type: str  # "linear" | "undulating" | "block"
    duration_weeks: int      # 4, 6, or 8
    equipment_json: str      # JSON list
    status: str              # "active" | "completed" | "paused"
    created_at: datetime

class ProgramSession(Base):
    id: str
    program_id: str          # FK → Program
    week_num: int            # 1-based
    day_num: int             # 1-based within the week
    focus: str               # "Upper Body Push", "Lower Body", "Full Body", etc.
    garmin_payload_json: str # Full Garmin API payload (same as SavedPlan)
    exercises_json: str      # ExerciseInfo list (same as SavedPlan)
    garmin_workout_id: str | None  # Set after upload
    scheduled_date: date | None    # Set after scheduling
    completed_at: datetime | None  # Set by Workout Player
```

### What's involved
- 1 new Alembic migration (2 tables, 2 indexes)
- New routes: `GET/POST /my/programs`, `DELETE /my/programs/{id}`, `GET /my/programs/{id}`
- Template: `my_programs.html` (list + detail view)
- Update `my_plans.html` to link plans to programs (optional)

### Dependencies
None — this is the foundation.

---

## Initiative 2: Multi-week Program Generator

**Priority:** Critical
**Effort:** 3–4 weeks
**Risk:** Medium (periodization logic is domain-specific; requires fitness knowledge)
**Depends on:** Initiative 1

### Current state
`web/workout_generator.py` → `generate()` produces one session. There is no concept of
accumulation/intensification phases, deload weeks, or session sequencing.

### The vision
A new `generate_program()` function takes `goal`, `equipment`, `weekly_workout_days`,
`fitness_level`, and `duration_weeks` and returns a fully structured `Program` object with all
sessions generated, named, and organized.

### Periodization structure (8-week example)

| Weeks | Phase | Volume | Intensity | Rep Range |
|-------|-------|--------|-----------|-----------|
| 1–3 | Accumulation | High | Moderate | 12–15 reps |
| 4 | Deload | 60% | Low | 12–15 reps |
| 5–7 | Intensification | Moderate | High | 6–10 reps |
| 8 | Peak / Test | Low | Max | 3–5 reps |

### Session split patterns (auto-selected by `weekly_workout_days`)

| Days/week | Pattern |
|-----------|---------|
| 2 | Full Body A / Full Body B |
| 3 | Push / Pull / Legs |
| 4 | Upper Push / Lower / Upper Pull / Lower |
| 5 | Push / Pull / Legs / Upper / Lower |

### What's involved
- New `generate_program()` function in `workout_generator.py`
- Phase-aware rep/set targets passed into `ExerciseBlock` (sets 3→4, reps 15→8 as phases progress)
- Session focus labels: "Upper Body Push", "Lower Body Hinge", "Full Body Power"
- Workout names: `"Week 2 Day 3 · Push — 45min"`
- New route `POST /my/programs/generate` → returns program preview
- New template: program wizard UI (goal → equipment → days/week → duration → preview)

### Dependencies
Initiative 1 (Program Data Model)

---

## Initiative 3: Garmin Calendar Batch Scheduling

**Priority:** High
**Effort:** 2–3 weeks
**Risk:** Medium (Garmin API rate limits; 1s inter-call delay means 56 sessions = ~1 min upload time)
**Depends on:** Initiative 2

### Current state
`GarminForgeClient.upload_and_schedule()` uploads and schedules **one** workout at a time.
An 8-week × 3-day program = 24 sessions; there's no bulk operation.

### The vision
A "Schedule full program" action that:
1. Uploads all N workout payloads to Garmin (with backoff)
2. Distributes sessions across dates matching `weekly_workout_days`, starting from a chosen date
3. Stores `garmin_workout_id` and `scheduled_date` on each `ProgramSession`
4. Shows a calendar preview before confirming

### New client method

```python
async def schedule_program(
    self,
    sessions: list[ProgramSession],
    start_date: date,
    days_per_week: int,
) -> list[tuple[str, date]]:
    """Upload all sessions and schedule them. Returns list of (workout_id, date) pairs."""
```

### Date distribution logic
- Pick the next N weekdays from `start_date` that match user's preferred training days
- Enforce minimum 1 rest day between strength sessions
- Skip already-scheduled dates (check Garmin calendar first)

### UI
- "Schedule Program" button → calendar preview modal showing 8 weeks of planned sessions
- Confirm → progress bar as uploads happen (Server-Sent Events or polling)
- Error recovery: if one upload fails, show which sessions succeeded and allow retry

### Dependencies
Initiative 2 (Program Generator)

---

## Initiative 4: Progressive Overload Engine

**Priority:** High
**Effort:** 3–4 weeks
**Risk:** Medium
**Depends on:** Initiative 1

### Current state
`WorkoutSession` records that a session happened, but not **what weight was used** or **how
many reps were completed** per exercise. There's no concept of a personal record (PR) or
progressive overload recommendation.

### The vision
After each session, the user logs (or the Workout Player app reports) actual performance:
sets completed, reps per set, and weight used. The next time they see that exercise, GarminForge
shows: `"Last time: 3×10 @ 60 kg → Target today: 3×12 @ 60 kg → Next: 3×10 @ 65 kg"`.

### Data model additions

```python
# Extend WorkoutSession:
exercise_logs_json: str | None
# JSON: [{"exercise_name": "BARBELL_BENCH_PRESS", "sets": [{"reps": 10, "weight_kg": 60.0}]}]

class PersonalRecord(Base):
    id: str
    user_id: str
    exercise_name: str      # e.g. "BARBELL_BENCH_PRESS"
    weight_kg: float
    reps: int
    achieved_at: datetime
    program_session_id: str | None
```

### Progression rules

```python
def next_target(history: list[ExerciseLog], target_reps: int) -> ExerciseTarget:
    last = history[-1]
    all_reps_hit = all(s.reps >= target_reps for s in last.sets)
    if all_reps_hit:
        return ExerciseTarget(reps=target_reps, weight_kg=last.weight_kg * 1.025)  # +2.5%
    elif last.sets[0].reps < target_reps * 0.8:
        return ExerciseTarget(reps=target_reps, weight_kg=last.weight_kg * 0.95)   # -5%
    else:
        return ExerciseTarget(reps=target_reps, weight_kg=last.weight_kg)           # repeat
```

### UI
- `workout_preview.html`: below each exercise, show "Last: 3×10 @ 60kg" if history exists
- `my_progress.html`: add PR table showing all-time bests per exercise
- New route `POST /my/sessions/{id}/logs` to accept detailed exercise logs

### Dependencies
Initiative 1 (Program Data Model)

---

## Initiative 5: Garmin Activity Data Sync

**Priority:** Medium
**Effort:** 3–4 weeks
**Risk:** High (Garmin activity data format is device/firmware-dependent; exercise parsing is noisy)
**Depends on:** Initiative 4

### Current state
`GarminForgeClient.get_activities()` is implemented but never called from any web route.
The Garmin activity API returns strength training sessions with exercise names, sets, and reps
in a proprietary format.

### The vision
Import a user's **existing Garmin workout history** to:
1. Seed the progressive overload engine (so it has data even for new users)
2. Show a "Garmin History" view with past performance on each exercise
3. Use inferred volume/intensity to place the user correctly in a new program

### Key technical challenges
- Garmin exercise names use FIT SDK keys (same as local catalog); `exercises.py` `resolve()`
  already handles fuzzy matching — reuse this
- Not all Garmin devices record per-set data; some only record total reps per exercise
- Rate limiting: fetching 1 year of history = ~52 API calls at 1s delay = ~52 seconds

### What's involved
- New route `POST /my/garmin-sync` → triggers background import job
- Activity parser: map Garmin activity exercise entries → `ExerciseLog` objects
- Conflict resolution: don't overwrite manually-entered logs
- Progress indicator (SSE or polling) since import takes ~1 minute for a year of history

### Dependencies
Initiative 4 (Progressive Overload Engine) — needs the `exercise_logs_json` schema

---

## Initiative 6: Adaptive Difficulty from Garmin Metrics

**Priority:** Medium
**Effort:** 2–3 weeks
**Risk:** High (many Garmin devices don't expose HRV or Body Battery via the Connect API)
**Depends on:** Initiative 5

### Current state
The user's `fitness_level` is a static questionnaire answer (Beginner/Intermediate/Advanced)
that never updates. Session intensity is fixed per goal — there's no feedback loop.

### The vision
Use live Garmin device metrics to make the program **self-adjusting**:

| Metric | Source | Use |
|--------|--------|-----|
| VO2max trend | `/usermetrics` | Auto-update fitness_level; show "fitness age improved" |
| Body Battery | `/dailySummary` | Warn "recovery low — consider lighter session today" |
| HRV status | `/hrv` | Flag deload week if HRV consistently below baseline |
| Resting heart rate trend | `/dailySummary` | Long-term fitness progress indicator |

### What's involved
- New `get_recovery_snapshot()` method in `GarminForgeClient`
- Dashboard widget: "Today's readiness" card (green/yellow/red)
- Program generator integration: if readiness < threshold on a scheduled session date,
  offer to swap to the deload variant
- VO2max chart on the progress page (time-series, pulled fresh on page load)

### Risk note
HRV and Body Battery are not available via the public Garmin Connect API for all devices.
The `/hrv` endpoint works for Fenix/Epix class watches; FR255/265 users may get no data.
Plan for graceful degradation: show the widget only when data is available.

### Dependencies
Initiative 5 (Garmin Activity Sync) — establishes the data-pull pattern

---

## Initiative 7: Program Library (Pre-built Templates)

**Priority:** Medium
**Effort:** 3–4 weeks
**Risk:** Low
**Depends on:** Initiative 2

### Current state
Every program is generated from scratch. There are no curated, evidence-based templates
a user can browse and adopt.

### The vision
A catalog of proven training frameworks, each represented as a `Program` template that can
be applied to the user's equipment and schedule:

| Template | Structure | Best for |
|----------|-----------|----------|
| Push / Pull / Legs | 3-day split, 6-week linear | Intermediate hypertrophy |
| Upper / Lower | 4-day split, 8-week | Strength + size |
| Full Body 3× | 3-day, 8-week undulating | Beginners, time-limited |
| 5/3/1 (Wendler) | 4-day, 4-week cycles | Strength-focused intermediate |
| GZCLP | 3-day, linear | Beginner strength |

Each template is parameterized: plug in the user's equipment and the generator fills in
appropriate exercises.

### What's involved
- `ProgramTemplate` data structure (JSON files in `web/templates/programs/`)
- Template browser UI: card grid with description, difficulty, focus, duration
- "Use this template" → customization wizard → generates Program
- Shareable program link (public read-only URL): `GET /programs/share/{token}`

### Dependencies
Initiative 2 (Program Generator) — templates are just parameterized inputs to the same engine

---

## Initiative 8: Running + Strength Hybrid Programs

**Priority:** Lower
**Effort:** 3–4 weeks
**Risk:** Low
**Depends on:** Initiatives 2, 3

### Current state
`RunningWorkoutBuilder` exists in `garminforge/workouts/running.py` and is fully functional,
but the web app only generates strength workouts. The two builders are never combined.

### The vision
A "Hybrid Athlete" program type that interleaves strength and running sessions across the week,
respecting interference constraints (no hard leg day the day before a long run).

### Distribution rules

```
3 strength + 2 run days:
  Mon: Strength (Lower)  Tue: Run (Easy)  Wed: Strength (Upper)
  Thu: Run (Intervals)   Fri: Strength (Full Body)

2 strength + 3 run days:
  Mon: Run (Easy)  Tue: Strength (Upper)  Wed: Run (Intervals)
  Thu: Rest        Fri: Strength (Lower)  Sat: Run (Long)
```

### What's involved
- Extend `generate_program()` to accept `include_running: bool` and `running_goal`
- Add `session_type: "strength" | "running"` to `ProgramSession`
- Running session generator: wraps existing `RunningWorkoutBuilder` with phase-aware intensity
  (easy in accumulation, tempo + intervals in intensification)
- Upload router: detect session type, use appropriate payload builder

### Dependencies
Initiative 2 (Program Generator), Initiative 3 (Calendar Scheduling)

---

## Timeline Summary

| Phase | Initiatives | Horizon | Key Deliverable |
|-------|-------------|---------|-----------------|
| **Foundation** | Initiative 1 + Quick Wins 1–6 | Months 1–2 | Program data model; personalized single sessions |
| **Core** | Initiatives 2 + 3 | Months 3–5 | Full multi-week program generator + calendar scheduling |
| **Intelligence** | Initiatives 4 + 5 | Months 6–9 | Progressive overload tracking + Garmin history import |
| **Mastery** | Initiatives 6, 7, 8 | Months 10–15 | Adaptive programs; program library; hybrid training |

---

## Effort & Risk Summary

| Initiative | Effort | Risk | Priority | Depends on |
|------------|--------|------|----------|------------|
| 1 — Program Data Model | 1–2 wks | Low | Critical | — |
| 2 — Program Generator | 3–4 wks | Medium | Critical | 1 |
| 3 — Calendar Batch Scheduling | 2–3 wks | Medium | High | 2 |
| 4 — Progressive Overload | 3–4 wks | Medium | High | 1 |
| 5 — Garmin Activity Sync | 3–4 wks | High | Medium | 4 |
| 6 — Adaptive Difficulty | 2–3 wks | High | Medium | 5 |
| 7 — Program Library | 3–4 wks | Low | Medium | 2 |
| 8 — Hybrid Programs | 3–4 wks | Low | Lower | 2, 3 |

---

## Risk Mitigation

**Garmin API rate limits (Initiatives 3, 5):**
`GarminForgeClient` already implements exponential backoff via `with_backoff()`. For bulk
operations, add a progress indicator and break uploads into resumable batches stored in the DB.

**Device capability variance (Initiative 6):**
Always check for `null` before rendering Garmin metric widgets. Design the recovery card with
a "data unavailable for your device" fallback state from day one.

**Periodization complexity (Initiative 2):**
Start with linear periodization only (simplest, most evidence-backed for beginners/intermediate).
Add undulating periodization in a later iteration. Don't try to model all systems at once.

**Exercise log data quality (Initiative 4):**
The Workout Player app may report incomplete logs (e.g., sets completed but no weight). Handle
optional `weight_kg` gracefully — progression rules should degrade to rep-only tracking when
weight data is absent.

---

## Alternative Direction: Deep Garmin Data Integration

*Not the primary roadmap, but the most natural extension of Initiatives 5 + 6.*

GarminForge can already query endpoints that no other third-party fitness app uses well:
- **VO2max + fitness age** — auto-calibrate difficulty over time
- **Body Battery / HRV** — recovery-aware scheduling
- **Body composition** — BMI-aware calorie burn, nutrition context
- **Heart rate zones** (device-specific) — replace generic pace zones in `RunningWorkoutBuilder`
- **Step count / active minutes** — factor daily movement into weekly volume

All API hooks exist in `GarminForgeClient.get_activities()`, `get_user_profile()`, and the
raw `connectapi` access via `_garth()`. This becomes most powerful as the intelligence layer
(Initiatives 5 + 6) matures.
