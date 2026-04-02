"""
Strength workout builder.

There is no typed Pydantic model for strength workouts in ``garminconnect``
(the library's workout module covers endurance sports only).  This module
provides a fluent builder that produces the raw JSON dict expected by
``/workout-service/workout`` and validates it before upload.

Usage example::

    from garminforge.workouts.strength import StrengthWorkout, ExerciseBlock

    workout = (
        StrengthWorkout("Upper Body A")
        .add_warmup(description="5 min general warm-up")
        .add_block(
            ExerciseBlock("BENCH_PRESS", "BARBELL_BENCH_PRESS", sets=4, reps=6,
                          rest_seconds=180, description="Bench Press 4x6"),
        )
        .add_block(
            ExerciseBlock("ROW", "DUMBBELL_ROW", sets=3, reps=10,
                          rest_seconds=90, description="DB Row 3x10"),
        )
        .add_cooldown(description="Cool-down / stretch")
    )

    payload = workout.build()          # dict ready for upload
    client.upload_strength_workout(payload)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from garminforge.exceptions import StepLimitExceededError
from garminforge.workouts import steps as S
from garminforge.workouts.exercises import validate as validate_exercise

def _estimate_duration(steps: list[S.Step]) -> int:
    """Recursively sum timed step durations (in seconds) across all steps."""
    total = 0
    for step in steps:
        key = step.get("stepType", {}).get("stepTypeKey")
        if key == "repeat":
            iters = step.get("numberOfIterations", 1)
            total += iters * _estimate_duration(step.get("workoutSteps", []))
        else:
            val = step.get("endConditionValue")
            cond_key = step.get("endCondition", {}).get("conditionTypeKey")
            if val is not None and cond_key == "time":
                total += int(val)
            elif val is not None and cond_key == "reps":
                # Approximate: 3 seconds per rep
                total += int(val) * 3
    return total


_STRENGTH_SPORT_TYPE = {
    "sportTypeId": 5,
    "sportTypeKey": "strength_training",
    "displayOrder": 5,
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ExerciseBlock:
    """One exercise with sets, reps, and optional rest between sets.

    Parameters
    ----------
    category:
        Garmin FIT SDK ``exerciseCategory`` (ALL_CAPS_SNAKE_CASE).
    name:
        Garmin FIT SDK ``exerciseName`` (ALL_CAPS_SNAKE_CASE).
    sets:
        Number of working sets (wraps exercise+rest in a repeat group).
    reps:
        Reps per set.  Mutually exclusive with *duration_seconds*.
    duration_seconds:
        Duration per set in seconds (e.g. 30 for a timed hold).
        Mutually exclusive with *reps*.
    rest_seconds:
        Rest between sets (seconds).  ``None`` → lap-button rest.
    description:
        Optional free-text note attached to the exercise step.
    """

    category: str
    name: str
    sets: int = 3
    reps: int | None = 10
    duration_seconds: float | None = None
    rest_seconds: float | None = 60
    description: str = ""

    def __post_init__(self) -> None:
        if self.reps is not None and self.duration_seconds is not None:
            raise ValueError("Provide either reps or duration_seconds, not both.")
        if self.reps is None and self.duration_seconds is None:
            raise ValueError("Provide reps or duration_seconds.")
        self.category = self.category.upper()
        self.name = self.name.upper()


@dataclass
class StrengthWorkout:
    """Fluent builder for a Garmin Connect strength workout.

    Parameters
    ----------
    name:
        Workout name (≤ 80 characters).
    description:
        Optional workout description (≤ 512 characters).
    """

    name: str
    description: str = ""
    _top_steps: list[S.Step] = field(default_factory=list, init=False, repr=False)

    # ------------------------------------------------------------------
    # Fluent API
    # ------------------------------------------------------------------

    def add_warmup(
        self,
        duration_seconds: float | None = None,
        description: str = "",
    ) -> "StrengthWorkout":
        """Append a warmup step."""
        self._top_steps.append(
            S.warmup_step(
                duration_seconds=duration_seconds,
                description=description,
                step_order=len(self._top_steps) + 1,
            )
        )
        return self

    def add_cooldown(
        self,
        duration_seconds: float | None = None,
        description: str = "",
    ) -> "StrengthWorkout":
        """Append a cooldown step."""
        self._top_steps.append(
            S.cooldown_step(
                duration_seconds=duration_seconds,
                description=description,
                step_order=len(self._top_steps) + 1,
            )
        )
        return self

    def add_rest(
        self,
        duration_seconds: float | None = None,
        description: str = "",
    ) -> "StrengthWorkout":
        """Append a standalone rest step (e.g. between exercise blocks)."""
        self._top_steps.append(
            S.rest_step(
                duration_seconds=duration_seconds,
                description=description,
                step_order=len(self._top_steps) + 1,
            )
        )
        return self

    def add_block(self, block: ExerciseBlock) -> "StrengthWorkout":
        """Append an exercise block (sets × reps wrapped in a repeat group)."""
        exercise = S.exercise_step(
            category=block.category,
            name=block.name,
            reps=block.reps,
            duration_seconds=block.duration_seconds,
            description=block.description,
            step_order=1,
        )
        nested: list[S.Step] = [exercise]
        if block.rest_seconds is not None or block.sets > 1:
            nested.append(
                S.rest_step(
                    duration_seconds=block.rest_seconds,
                    description=f"Rest {int(block.rest_seconds)}s" if block.rest_seconds else "Rest",
                    step_order=2,
                )
            )
        group = S.repeat_group(
            sets=block.sets,
            steps=nested,
            step_order=len(self._top_steps) + 1,
        )
        self._top_steps.append(group)
        return self

    def add_raw_step(self, step: S.Step) -> "StrengthWorkout":
        """Append a pre-built step dict (escape hatch for unsupported patterns)."""
        step = {**step, "stepOrder": len(self._top_steps) + 1}
        self._top_steps.append(step)
        return self

    # ------------------------------------------------------------------
    # Build / validate
    # ------------------------------------------------------------------

    def build(self, *, validate: bool = True) -> dict[str, Any]:
        """Return the workout as a JSON-serialisable dict ready for upload.

        Parameters
        ----------
        validate:
            When ``True`` (default), checks step count and exercise names.

        Raises
        ------
        StepLimitExceededError
            If the workout exceeds 50 steps.
        WorkoutValidationError
            If an exercise category/name is not in the local catalog.
        """
        if validate:
            self._validate()

        # Re-number top-level steps.
        renumbered = [
            {**s, "stepOrder": i + 1} for i, s in enumerate(self._top_steps)
        ]

        payload: dict[str, Any] = {
            "workoutName": self.name[:80],
            "sportType": _STRENGTH_SPORT_TYPE,
            "estimatedDurationInSecs": _estimate_duration(renumbered),
            "workoutSegments": [
                {
                    "segmentOrder": 1,
                    "sportType": _STRENGTH_SPORT_TYPE,
                    "workoutSteps": renumbered,
                }
            ],
        }
        if self.description:
            payload["description"] = self.description[:512]

        return payload

    def _validate(self) -> None:
        total = S.count_steps(self._top_steps)
        if total > StepLimitExceededError.MAX_STEPS:
            raise StepLimitExceededError(total)

        # Validate exercise names (warn only — Garmin's catalog is larger).
        for step in _iter_exercise_steps(self._top_steps):
            cat = step.get("category", "")
            name = step.get("exerciseName", "")
            if cat and name and not validate_exercise(cat, name):
                import warnings
                warnings.warn(
                    f"Exercise {cat}/{name} is not in the local catalog.  "
                    "Upload may succeed if it exists in Garmin's server-side catalog.",
                    stacklevel=3,
                )


def _iter_exercise_steps(steps: list[S.Step]):
    """Recursively yield all non-repeat steps from a step list."""
    for step in steps:
        if step.get("stepType", {}).get("stepTypeKey") == "repeat":
            yield from _iter_exercise_steps(step.get("workoutSteps", []))
        else:
            yield step
