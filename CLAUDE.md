# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

GarminForge is a Python toolkit for creating, uploading, and scheduling Garmin Connect workouts. It has two layers:

1. **`garminforge/` — core library**: Workout builders, auth/token management, and a `GarminForgeClient` that wraps `garminconnect`.
2. **`web/` — FastAPI web app**: A browser UI where users log in, pick a goal/equipment/duration, preview a generated workout, and push it to Garmin Connect.

## Installation

```bash
# Core library only
pip install -e .

# Core + web server
pip install -e ".[web]"

# Core + web + dev tools
pip install -e ".[web,dev]"
```

## Running the web server

```bash
python run.py                        # http://127.0.0.1:8000
python run.py --port 8080 --reload   # dev mode with auto-reload
```

Environment variables:
- `SECRET_KEY` — session signing key (auto-generated if omitted; set a stable value in production)
- `GARMINTOKENS` — path to token directory (default: `~/.garminconnect`)

## Linting / type checking / tests

```bash
ruff check .                  # lint
ruff format .                 # format
mypy garminforge web          # type check (strict)
pytest                        # run all tests
pytest tests/test_strength.py # run a single test file
pytest -k "test_name"         # run tests matching a name pattern
```

## Authentication architecture

**Important caveat**: Garmin's SSO broke in March 2026. Fresh logins (`interactive_login()`) may fail. The intended workflow is to generate tokens on a machine where auth still works, then transfer the token directory (`~/.garminconnect`) or base64 string to other environments.

`TokenStore` (`garminforge/auth.py`) supports two storage modes:
- **Directory mode** (default): reads/writes `oauth1_token.json` + `oauth2_token.json` in `~/.garminconnect`.
- **String mode**: a base64 blob from `garth.dumps()`, suitable for env vars or secrets managers — use `from_token_string()`.

`load_client()` → populates a `Garmin()` instance from stored tokens. `GarminForgeClient` lazily calls this on first use and wraps every API call with exponential backoff via `with_backoff()`.

## Workout builder architecture

All builders produce a `dict[str, Any]` payload ready to POST to `/workout-service/workout`.

**Strength workouts** (`garminforge/workouts/strength.py`):
- `StrengthWorkout` (fluent builder) + `ExerciseBlock` (one exercise with sets/reps/rest)
- Each `ExerciseBlock` becomes a `repeat` group wrapping an exercise step + rest step
- Exercise category/name values must match Garmin's FIT SDK keys (ALL_CAPS_SNAKE_CASE); the local catalog is in `garminforge/workouts/exercises.py`

**Running workouts** (`garminforge/workouts/running.py`):
- `RunningWorkoutBuilder` (fluent) with `.warmup()`, `.easy()`, `.tempo()`, `.repeat()`, `.cooldown()`
- Pace targets expressed in seconds/km; use `pace_from_min_per_km("4:30")` to convert

**Step primitives** (`garminforge/workouts/steps.py`): low-level dicts (`warmup_step`, `rest_step`, `interval_step`, `repeat_group`, etc.) shared by both builders.

**50-step limit**: Garmin enforces a hard limit of 50 steps per workout. `StepLimitExceededError` is raised by `.build()` when exceeded. `count_steps()` recursively counts steps through repeat groups.

## Web app architecture

`web/app.py` — FastAPI application (Starlette sessions, Jinja2 templates).

Key routes:
- `GET /` — login form
- `POST /login` — calls `interactive_login()`, stores token string in session
- `GET /dashboard` — workout configuration form (goal, equipment, duration)
- `POST /generate` — calls `web.workout_generator.generate()`, stores `WorkoutPlan` in session, redirects to preview
- `GET /preview` — renders workout preview with exercise list
- `POST /upload` — calls `GarminForgeClient.upload_and_schedule()`

`web/workout_generator.py` — stateless `generate(equipment, goal, duration_minutes)` function that selects exercises from a pool (`_POOL`), builds a `StrengthWorkout`, and returns a `WorkoutPlan` dataclass containing both the Garmin payload and rich metadata for the UI.

`web/exercise_links.py` — maps exercise names to tutorial/reference URLs shown in the workout preview.

## Key constraints to keep in mind

- The 50-step limit is a hard Garmin server constraint, not just a local check.
- Rate limits: 1 s inter-call delay by default in `GarminForgeClient`; login endpoint triggers a 15-min lockout after ~5–10 rapid attempts.
- `garth` version is pinned to `<0.9` due to API compatibility; `auth.py` has a `_garth()` compatibility shim for garminconnect versions that expose `client.garth` vs. the module-level client.
- `ruff` line length is 100; `mypy` is set to strict mode.
