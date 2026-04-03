"""
Low-level workout step builders.

Every function in this module returns a plain ``dict`` that maps directly to
the JSON schema accepted by ``/workout-service/workout``.  Higher-level
modules (strength.py, running.py) call these builders so the JSON structure
is defined in one place.

Key constraints from the Garmin Connect API:
- ``endConditionValue`` is a top-level field on the step (seconds for time,
  reps count for reps, iterations count for repeat groups).
- ``endCondition`` contains only type metadata (no value).
- Steps require a ``type`` discriminator field: ``"ExecutableStepDTO"`` or
  ``"RepeatGroupDTO"``.
- Maximum 50 steps per workout (enforced by ``GarminForgeClient``).
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Internal type alias
# ---------------------------------------------------------------------------

Step = dict[str, Any]


# ---------------------------------------------------------------------------
# End-condition helpers
# (value goes in endConditionValue at step level, not here)
# ---------------------------------------------------------------------------


def _time_condition() -> dict[str, Any]:
    return {
        "conditionTypeId": 2,
        "conditionTypeKey": "time",
        "displayOrder": 2,
        "displayable": True,
    }


def _reps_condition() -> dict[str, Any]:
    return {
        "conditionTypeId": 10,
        "conditionTypeKey": "reps",
        "displayOrder": 10,
        "displayable": True,
    }


def _distance_condition() -> dict[str, Any]:
    return {
        "conditionTypeId": 3,
        "conditionTypeKey": "distance",
        "displayOrder": 3,
        "displayable": True,
    }


def _lap_button_condition() -> dict[str, Any]:
    return {
        "conditionTypeId": 1,
        "conditionTypeKey": "lap.button",
        "displayOrder": 1,
        "displayable": True,
    }


def _iterations_condition() -> dict[str, Any]:
    return {
        "conditionTypeId": 7,
        "conditionTypeKey": "iterations",
        "displayOrder": 7,
        "displayable": False,
    }


# ---------------------------------------------------------------------------
# Target-type helpers
# ---------------------------------------------------------------------------


def no_target() -> dict[str, Any]:
    return {
        "workoutTargetTypeId": 1,
        "workoutTargetTypeKey": "no.target",
        "displayOrder": 1,
    }


def heart_rate_zone_target(zone: int) -> dict[str, Any]:
    """Heart rate zone target (1–5)."""
    return {
        "workoutTargetTypeId": 4,
        "workoutTargetTypeKey": "heart.rate.zone",
        "displayOrder": 4,
        "targetValueOne": zone,
        "targetValueTwo": zone,
    }


def pace_zone_target(min_pace_sec_per_km: float, max_pace_sec_per_km: float) -> dict[str, Any]:
    """Pace zone target — values in **seconds per kilometre**."""
    return {
        "workoutTargetTypeId": 6,
        "workoutTargetTypeKey": "pace.zone",
        "displayOrder": 6,
        "targetValueOne": min_pace_sec_per_km,
        "targetValueTwo": max_pace_sec_per_km,
    }


# ---------------------------------------------------------------------------
# Generic step factories
# ---------------------------------------------------------------------------


def warmup_step(
    *,
    duration_seconds: float | None = None,
    description: str = "",
    step_order: int = 1,
) -> Step:
    """Create a warmup step.

    If *duration_seconds* is ``None`` the step ends on a lap-button press.
    """
    if duration_seconds is not None:
        end_condition = _time_condition()
        end_condition_value: float | None = duration_seconds
    else:
        end_condition = _lap_button_condition()
        end_condition_value = None

    step: Step = {
        "type": "ExecutableStepDTO",
        "stepOrder": step_order,
        "stepType": {"stepTypeId": 1, "stepTypeKey": "warmup", "displayOrder": 1},
        "endCondition": end_condition,
        "endConditionValue": end_condition_value,
        "targetType": no_target(),
    }
    if description:
        step["description"] = description
    return step


def cooldown_step(
    *,
    duration_seconds: float | None = None,
    description: str = "",
    step_order: int = 1,
) -> Step:
    """Create a cooldown step (lap-button by default)."""
    if duration_seconds is not None:
        end_condition = _time_condition()
        end_condition_value: float | None = duration_seconds
    else:
        end_condition = _lap_button_condition()
        end_condition_value = None

    step: Step = {
        "type": "ExecutableStepDTO",
        "stepOrder": step_order,
        "stepType": {"stepTypeId": 2, "stepTypeKey": "cooldown", "displayOrder": 2},
        "endCondition": end_condition,
        "endConditionValue": end_condition_value,
        "targetType": no_target(),
    }
    if description:
        step["description"] = description
    return step


def rest_step(
    *,
    duration_seconds: float | None = None,
    description: str = "",
    step_order: int = 1,
) -> Step:
    """Create a rest step.

    If *duration_seconds* is ``None`` the step ends on a lap-button press.
    """
    if duration_seconds is not None:
        end_condition = _time_condition()
        end_condition_value: float | None = duration_seconds
    else:
        end_condition = _lap_button_condition()
        end_condition_value = None

    step: Step = {
        "type": "ExecutableStepDTO",
        "stepOrder": step_order,
        "stepType": {"stepTypeId": 5, "stepTypeKey": "rest", "displayOrder": 5},
        "endCondition": end_condition,
        "endConditionValue": end_condition_value,
        "targetType": no_target(),
    }
    if description:
        step["description"] = description
    return step


def interval_step(
    *,
    duration_seconds: float | None = None,
    distance_meters: float | None = None,
    reps: int | None = None,
    target: dict[str, Any] | None = None,
    description: str = "",
    step_order: int = 1,
) -> Step:
    """Create an active interval step.

    Exactly one of *duration_seconds*, *distance_meters*, or *reps* must be
    provided.  If none is given, defaults to lap-button.
    """
    if sum(x is not None for x in (duration_seconds, distance_meters, reps)) > 1:
        raise ValueError(
            "Provide at most one of duration_seconds, distance_meters, or reps."
        )
    if duration_seconds is not None:
        end_condition = _time_condition()
        end_condition_value: float | None = duration_seconds
    elif distance_meters is not None:
        end_condition = _distance_condition()
        end_condition_value = distance_meters
    elif reps is not None:
        end_condition = _reps_condition()
        end_condition_value = float(reps)
    else:
        end_condition = _lap_button_condition()
        end_condition_value = None

    step: Step = {
        "type": "ExecutableStepDTO",
        "stepOrder": step_order,
        "stepType": {"stepTypeId": 3, "stepTypeKey": "interval", "displayOrder": 3},
        "endCondition": end_condition,
        "endConditionValue": end_condition_value,
        "targetType": target or no_target(),
    }
    if description:
        step["description"] = description
    return step


def exercise_step(
    *,
    category: str,
    name: str,
    reps: int | None = None,
    duration_seconds: float | None = None,
    description: str = "",
    step_order: int = 1,
) -> Step:
    """Create a strength exercise step.

    Parameters
    ----------
    category:
        ``exerciseCategory`` ALL_CAPS_SNAKE_CASE string, e.g. ``"BENCH_PRESS"``.
    name:
        ``exerciseName`` ALL_CAPS_SNAKE_CASE string, e.g. ``"BARBELL_BENCH_PRESS"``.
    reps:
        End condition by rep count (mutually exclusive with *duration_seconds*).
    duration_seconds:
        End condition by time (mutually exclusive with *reps*).
    """
    if reps is not None and duration_seconds is not None:
        raise ValueError("Provide either reps or duration_seconds, not both.")

    if reps is not None:
        end_condition = _reps_condition()
        end_condition_value: int | None = int(reps)
    elif duration_seconds is not None:
        end_condition = _time_condition()
        end_condition_value = duration_seconds
    else:
        end_condition = _lap_button_condition()
        end_condition_value = None

    step: Step = {
        "type": "ExecutableStepDTO",
        "stepOrder": step_order,
        "stepType": {"stepTypeId": 3, "stepTypeKey": "interval", "displayOrder": 3},
        "category": category.upper(),
        "exerciseName": name.upper(),
        "endCondition": end_condition,
        "endConditionValue": end_condition_value,
        "targetType": no_target(),
    }
    if description:
        step["description"] = description
    return step


def repeat_group(
    sets: int,
    steps: list[Step],
    step_order: int = 1,
) -> Step:
    """Wrap *steps* in a repeat group representing *sets* sets.

    The ``stepOrder`` of each nested step is re-assigned starting from 1
    so the group is self-consistent regardless of the order steps were
    created in.

    Parameters
    ----------
    sets:
        Number of times to repeat the group (i.e. number of sets).
    steps:
        The steps to repeat (exercise + rest pairs, etc.).
    step_order:
        Position of this repeat group within its parent segment.
    """
    # Re-number nested steps.
    renumbered = [
        {**s, "stepOrder": i + 1} for i, s in enumerate(steps)
    ]
    return {
        "type": "RepeatGroupDTO",
        "stepOrder": step_order,
        "stepType": {"stepTypeId": 6, "stepTypeKey": "repeat", "displayOrder": 6},
        "numberOfIterations": sets,
        "endCondition": _iterations_condition(),
        "endConditionValue": float(sets),
        "workoutSteps": renumbered,
    }


# ---------------------------------------------------------------------------
# Counting helpers
# ---------------------------------------------------------------------------


def count_steps(steps: list[Step]) -> int:
    """Recursively count all individual steps (not repeat-group wrappers)."""
    total = 0
    for step in steps:
        if step.get("stepType", {}).get("stepTypeKey") == "repeat":
            total += count_steps(step.get("workoutSteps", []))
        else:
            total += 1
    return total
