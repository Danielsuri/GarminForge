"""
GarminForge workout builders.

Quick reference
---------------
Strength workouts::

    from garminforge.workouts.strength import StrengthWorkout, ExerciseBlock

Running workouts::

    from garminforge.workouts.running import RunningWorkoutBuilder, pace_from_min_per_km

Low-level step primitives::

    from garminforge.workouts.steps import (
        warmup_step, cooldown_step, rest_step,
        interval_step, exercise_step, repeat_group,
        count_steps,
    )

Exercise catalog::

    from garminforge.workouts.exercises import resolve, validate, all_exercises
"""

from garminforge.workouts.exercises import Exercise, resolve, validate, all_exercises
from garminforge.workouts.running import RunningWorkoutBuilder, pace_from_min_per_km
from garminforge.workouts.strength import ExerciseBlock, StrengthWorkout
from garminforge.workouts.steps import (
    cooldown_step,
    count_steps,
    exercise_step,
    interval_step,
    repeat_group,
    rest_step,
    warmup_step,
    heart_rate_zone_target,
    no_target,
    pace_zone_target,
)

__all__ = [
    # Strength
    "StrengthWorkout",
    "ExerciseBlock",
    # Running
    "RunningWorkoutBuilder",
    "pace_from_min_per_km",
    # Steps
    "warmup_step",
    "cooldown_step",
    "rest_step",
    "interval_step",
    "exercise_step",
    "repeat_group",
    "count_steps",
    "no_target",
    "heart_rate_zone_target",
    "pace_zone_target",
    # Exercises
    "Exercise",
    "resolve",
    "validate",
    "all_exercises",
]
