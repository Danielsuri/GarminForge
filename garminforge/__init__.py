"""
GarminForge — Python toolkit for creating, uploading, and scheduling
Garmin Connect workouts.

Quick start
-----------
1.  Generate tokens on a machine where you can authenticate interactively::

        from garminforge.auth import interactive_login, TokenStore
        _, store = interactive_login("you@example.com", "password")
        # tokens saved to ~/.garminconnect by default

2.  Build and upload a strength workout::

        from garminforge.client import GarminForgeClient
        from garminforge.workouts.strength import StrengthWorkout, ExerciseBlock

        client = GarminForgeClient()

        workout = (
            StrengthWorkout("Push Day")
            .add_warmup(description="General warm-up")
            .add_block(ExerciseBlock("BENCH_PRESS", "BARBELL_BENCH_PRESS",
                                     sets=4, reps=6, rest_seconds=180))
            .add_block(ExerciseBlock("SHOULDER_PRESS", "DUMBBELL_SHOULDER_PRESS",
                                     sets=3, reps=10, rest_seconds=90))
            .add_block(ExerciseBlock("TRICEPS_EXTENSION", "TRICEPS_PUSHDOWN",
                                     sets=3, reps=12, rest_seconds=60))
            .add_cooldown()
        )

        result = client.upload_workout(workout.build())
        client.schedule_workout(result["workoutId"], "2026-04-07")

3.  Build and upload an interval running workout::

        from garminforge.workouts.running import RunningWorkoutBuilder, pace_from_min_per_km

        run = (
            RunningWorkoutBuilder("5K Interval Session")
            .warmup(600)
            .repeat(6,
                work_duration=180,
                work_pace=(pace_from_min_per_km("4:00"), pace_from_min_per_km("4:15")),
                rest_duration=120)
            .cooldown(600)
        )

        result = client.upload_workout(run.build())

Notes
-----
- **Authentication caveat**: Garmin's SSO broke in March 2026; fresh logins
  may fail.  Generate tokens where possible and transfer them.
- **Rate limits**: The library sleeps 1 s between calls by default.  The login
  endpoint is the most aggressively rate-limited (≈5–10 rapid attempts → 15 min
  lockout).
- **50-step limit**: Garmin enforces a maximum of 50 steps per workout.  Use
  FIT files (``fit-tool`` package) to bypass this.
"""

from garminforge.auth import TokenStore, interactive_login, load_client
from garminforge.client import GarminForgeClient, from_token_dir, from_token_string
from garminforge.exceptions import (
    AuthenticationError,
    ConnectionError,
    GarminForgeError,
    StepLimitExceededError,
    TokenNotFoundError,
    TooManyRequestsError,
    WorkoutValidationError,
)
from garminforge.workouts import (
    ExerciseBlock,
    RunningWorkoutBuilder,
    StrengthWorkout,
    pace_from_min_per_km,
    resolve,
)

__version__ = "0.1.0"

__all__ = [
    # Client
    "GarminForgeClient",
    "from_token_string",
    "from_token_dir",
    # Auth
    "TokenStore",
    "interactive_login",
    "load_client",
    # Workout builders
    "StrengthWorkout",
    "ExerciseBlock",
    "RunningWorkoutBuilder",
    "pace_from_min_per_km",
    # Exercise catalog
    "resolve",
    # Exceptions
    "GarminForgeError",
    "AuthenticationError",
    "TokenNotFoundError",
    "TooManyRequestsError",
    "ConnectionError",
    "WorkoutValidationError",
    "StepLimitExceededError",
]
