"""
Example: upload a 3-day strength programme to Garmin Connect.

Run from the repo root:
    python examples/strength_workout.py

Prerequisites:
    1. pip install garminconnect[workout]
    2. Valid tokens in ~/.garminconnect (see garminforge.auth.interactive_login)
"""

import json
import logging
from datetime import date, timedelta

from garminforge import GarminForgeClient, StrengthWorkout, ExerciseBlock

logging.basicConfig(level=logging.INFO)


# ---------------------------------------------------------------------------
# Define three workouts
# ---------------------------------------------------------------------------

def build_push_day() -> dict:
    return (
        StrengthWorkout(
            "Push Day — Chest / Shoulders / Triceps",
            description="Horizontal + vertical push, triceps isolation.",
        )
        .add_warmup(description="5 min general warm-up + shoulder circles")
        .add_block(ExerciseBlock(
            "BENCH_PRESS", "BARBELL_BENCH_PRESS",
            sets=4, reps=6, rest_seconds=180,
            description="Bench Press 4×6 — controlled descent",
        ))
        .add_block(ExerciseBlock(
            "SHOULDER_PRESS", "DUMBBELL_SHOULDER_PRESS",
            sets=3, reps=10, rest_seconds=90,
            description="DB Shoulder Press 3×10",
        ))
        .add_block(ExerciseBlock(
            "FLYE", "INCLINE_DUMBBELL_FLYE",
            sets=3, reps=12, rest_seconds=60,
            description="Incline DB Flye 3×12",
        ))
        .add_block(ExerciseBlock(
            "TRICEPS_EXTENSION", "TRICEPS_PUSHDOWN",
            sets=3, reps=15, rest_seconds=60,
            description="Triceps Pushdown 3×15",
        ))
        .add_cooldown(description="Chest + shoulder stretch")
        .build()
    )


def build_pull_day() -> dict:
    return (
        StrengthWorkout(
            "Pull Day — Back / Biceps",
            description="Vertical + horizontal pull, biceps curl.",
        )
        .add_warmup(description="5 min warm-up + band pull-aparts")
        .add_block(ExerciseBlock(
            "DEADLIFT", "BARBELL_DEADLIFT",
            sets=4, reps=5, rest_seconds=240,
            description="Deadlift 4×5 — brace hard",
        ))
        .add_block(ExerciseBlock(
            "PULL_UP", "PULL_UP",
            sets=3, reps=8, rest_seconds=120,
            description="Pull-ups 3×8 (add weight if easy)",
        ))
        .add_block(ExerciseBlock(
            "ROW", "DUMBBELL_ROW",
            sets=3, reps=10, rest_seconds=90,
            description="DB Row 3×10 each side",
        ))
        .add_block(ExerciseBlock(
            "CURL", "BARBELL_CURL",
            sets=3, reps=12, rest_seconds=60,
            description="Barbell Curl 3×12",
        ))
        .add_cooldown(description="Lat + biceps stretch")
        .build()
    )


def build_leg_day() -> dict:
    return (
        StrengthWorkout(
            "Leg Day — Quads / Hamstrings / Glutes",
            description="Squat pattern, hip hinge, single-leg work.",
        )
        .add_warmup(description="5 min row/bike + hip mobility")
        .add_block(ExerciseBlock(
            "SQUAT", "BARBELL_BACK_SQUAT",
            sets=4, reps=6, rest_seconds=180,
            description="Back Squat 4×6 — hit depth",
        ))
        .add_block(ExerciseBlock(
            "DEADLIFT", "ROMANIAN_DEADLIFT",
            sets=3, reps=10, rest_seconds=120,
            description="RDL 3×10",
        ))
        .add_block(ExerciseBlock(
            "HIP_RAISE", "BARBELL_HIP_THRUST",
            sets=3, reps=12, rest_seconds=90,
            description="Hip Thrust 3×12",
        ))
        .add_block(ExerciseBlock(
            "LUNGE", "BULGARIAN_SPLIT_SQUAT",
            sets=3, reps=10, rest_seconds=90,
            description="Bulgarian Split Squat 3×10 each leg",
        ))
        .add_block(ExerciseBlock(
            "LEG_CURL", "LYING_LEG_CURL",
            sets=3, reps=12, rest_seconds=60,
            description="Leg Curl 3×12",
        ))
        .add_cooldown(description="Quad + hamstring stretch")
        .build()
    )


# ---------------------------------------------------------------------------
# Upload and schedule
# ---------------------------------------------------------------------------

def main() -> None:
    client = GarminForgeClient()

    # Start Monday of next week.
    today = date.today()
    next_monday = today + timedelta(days=(7 - today.weekday()) % 7 or 7)

    schedule = [
        (build_push_day(),  next_monday),
        (build_pull_day(),  next_monday + timedelta(days=2)),
        (build_leg_day(),   next_monday + timedelta(days=4)),
    ]

    for payload, workout_date in schedule:
        print(f"\nUploading {payload['workoutName']!r} …")

        # Dry-run: print JSON instead of uploading.
        # Comment out the block below and uncomment the upload lines to go live.
        print(json.dumps(payload, indent=2))
        print(f"  → Would schedule to {workout_date}")

        # Live upload (uncomment to use):
        # result = client.upload_workout(payload)
        # workout_id = result["workoutId"]
        # client.schedule_workout(workout_id, str(workout_date))
        # print(f"  → Scheduled workout {workout_id} on {workout_date}")


if __name__ == "__main__":
    main()
