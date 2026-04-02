"""
Example: upload a structured running week to Garmin Connect.

Run from the repo root:
    python examples/running_workout.py

Prerequisites:
    1. pip install garminconnect[workout]
    2. Valid tokens in ~/.garminconnect
"""

import json
import logging
from datetime import date, timedelta

from garminforge import GarminForgeClient
from garminforge.workouts.running import RunningWorkoutBuilder, pace_from_min_per_km

logging.basicConfig(level=logging.INFO)


# ---------------------------------------------------------------------------
# Workout templates
# ---------------------------------------------------------------------------

def build_easy_run(duration_minutes: int = 45) -> dict:
    """A simple easy run at conversational pace (HR zone 2)."""
    return (
        RunningWorkoutBuilder(
            f"Easy Run {duration_minutes}min",
            description="Zone 2 aerobic base building.",
        )
        .warmup(300, description="Easy warm-up jog")
        .easy(
            duration_seconds=(duration_minutes - 10) * 60,
            hr_zone=2,
            description="Easy aerobic run",
        )
        .cooldown(300, description="Easy cool-down jog")
        .build()
    )


def build_tempo_run() -> dict:
    """20-minute tempo effort sandwiched by warm-up and cool-down."""
    return (
        RunningWorkoutBuilder(
            "Tempo Run 20min",
            description="Sustained comfortably-hard effort (LT2 pace).",
        )
        .warmup(600, description="10 min easy warm-up")
        .tempo(
            duration_seconds=1200,
            pace_range=(
                pace_from_min_per_km("4:15"),
                pace_from_min_per_km("4:30"),
            ),
            description="Tempo @ 4:15–4:30/km",
        )
        .cooldown(600, description="10 min easy cool-down")
        .build()
    )


def build_interval_session() -> dict:
    """Classic 6×1km intervals at 5K pace."""
    return (
        RunningWorkoutBuilder(
            "6×1km Intervals",
            description="VO2max development — 6 reps at 5K race pace.",
        )
        .warmup(600, description="10 min easy warm-up")
        .repeat(
            6,
            work_distance_meters=1000,
            work_pace=(
                pace_from_min_per_km("3:50"),
                pace_from_min_per_km("4:00"),
            ),
            rest_duration=120,
            work_description="1km @ 5K pace",
            rest_description="2 min jog recovery",
        )
        .cooldown(600, description="10 min easy cool-down")
        .build()
    )


def build_long_run(distance_km: float = 20.0) -> dict:
    """Long run — single easy effort."""
    return (
        RunningWorkoutBuilder(
            f"Long Run {distance_km:.0f}km",
            description="Weekly long run for endurance adaptation.",
        )
        .warmup(300, description="5 min easy warm-up")
        .easy(
            distance_meters=distance_km * 1000,
            hr_zone=2,
            description=f"Long run {distance_km:.0f}km @ zone 2",
        )
        .cooldown(300, description="5 min easy cool-down")
        .build()
    )


# ---------------------------------------------------------------------------
# Upload and schedule
# ---------------------------------------------------------------------------

def main() -> None:
    client = GarminForgeClient()

    today = date.today()
    next_monday = today + timedelta(days=(7 - today.weekday()) % 7 or 7)

    schedule = [
        (build_easy_run(45),     next_monday),                     # Mon
        (build_interval_session(), next_monday + timedelta(days=1)),  # Tue
        (build_easy_run(40),     next_monday + timedelta(days=3)),  # Thu
        (build_tempo_run(),      next_monday + timedelta(days=4)),  # Fri
        (build_long_run(20),     next_monday + timedelta(days=6)),  # Sun
    ]

    for payload, workout_date in schedule:
        print(f"\nWorkout: {payload['workoutName']!r} — {workout_date}")
        print(json.dumps(payload, indent=2))
        print(f"  → Would schedule on {workout_date}")

        # Live upload (uncomment to use):
        # result = client.upload_workout(payload)
        # workout_id = result["workoutId"]
        # client.schedule_workout(workout_id, str(workout_date))
        # print(f"  → Uploaded {workout_id} and scheduled on {workout_date}")


if __name__ == "__main__":
    main()
