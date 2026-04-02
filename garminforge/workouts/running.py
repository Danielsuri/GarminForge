"""
Running workout builder.

Wraps the typed ``garminconnect.workout.RunningWorkout`` Pydantic model with
a higher-level fluent API for common training patterns:

- Easy / recovery runs (single continuous effort)
- Interval sessions (warm-up → N × work/rest → cool-down)
- Tempo runs (sustained effort with time or distance end condition)
- Long runs (distance-based with lap-button segments)

All pace targets are expressed in **seconds per kilometre**; helper
``pace_from_min_per_km()`` converts ``"4:30"``-style strings.

Usage::

    from garminforge.workouts.running import RunningWorkoutBuilder, pace_from_min_per_km

    workout = (
        RunningWorkoutBuilder("5K Interval Session")
        .warmup(600)
        .repeat(5,
            work_duration=180, work_pace=(pace_from_min_per_km("4:00"), pace_from_min_per_km("4:15")),
            rest_duration=120)
        .cooldown(600)
    )
    payload = workout.build()
"""

from __future__ import annotations

from typing import Any

from garminforge.exceptions import StepLimitExceededError
from garminforge.workouts import steps as S

_RUNNING_SPORT_TYPE = {
    "sportTypeId": 1,
    "sportTypeKey": "running",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def pace_from_min_per_km(pace_str: str) -> float:
    """Convert ``"M:SS"`` or ``"MM:SS"`` string to seconds per kilometre.

    >>> pace_from_min_per_km("4:30")
    270.0
    """
    parts = pace_str.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Expected pace as 'M:SS', got {pace_str!r}")
    minutes, seconds = int(parts[0]), int(parts[1])
    return float(minutes * 60 + seconds)


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


class RunningWorkoutBuilder:
    """Fluent builder for a running workout.

    Parameters
    ----------
    name:
        Workout name (≤ 80 characters).
    description:
        Optional description (≤ 512 characters).
    """

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self._steps: list[S.Step] = []

    # ------------------------------------------------------------------
    # Segment factories
    # ------------------------------------------------------------------

    def warmup(
        self,
        duration_seconds: float | None = None,
        description: str = "Warm-up",
    ) -> "RunningWorkoutBuilder":
        """Add a warmup step (lap-button if *duration_seconds* is ``None``)."""
        self._steps.append(
            S.warmup_step(
                duration_seconds=duration_seconds,
                description=description,
                step_order=len(self._steps) + 1,
            )
        )
        return self

    def cooldown(
        self,
        duration_seconds: float | None = None,
        description: str = "Cool-down",
    ) -> "RunningWorkoutBuilder":
        """Add a cooldown step."""
        self._steps.append(
            S.cooldown_step(
                duration_seconds=duration_seconds,
                description=description,
                step_order=len(self._steps) + 1,
            )
        )
        return self

    def easy(
        self,
        duration_seconds: float | None = None,
        distance_meters: float | None = None,
        pace_range: tuple[float, float] | None = None,
        hr_zone: int | None = None,
        description: str = "",
    ) -> "RunningWorkoutBuilder":
        """Add a continuous easy-effort interval.

        Provide *duration_seconds* **or** *distance_meters* (not both).
        *pace_range* is ``(min_sec_per_km, max_sec_per_km)``.
        """
        target = _make_target(pace_range, hr_zone)
        self._steps.append(
            S.interval_step(
                duration_seconds=duration_seconds,
                distance_meters=distance_meters,
                target=target,
                description=description,
                step_order=len(self._steps) + 1,
            )
        )
        return self

    def tempo(
        self,
        duration_seconds: float | None = None,
        distance_meters: float | None = None,
        pace_range: tuple[float, float] | None = None,
        hr_zone: int | None = None,
        description: str = "Tempo",
    ) -> "RunningWorkoutBuilder":
        """Add a tempo interval (same API as ``easy``)."""
        return self.easy(
            duration_seconds=duration_seconds,
            distance_meters=distance_meters,
            pace_range=pace_range,
            hr_zone=hr_zone,
            description=description,
        )

    def repeat(
        self,
        count: int,
        *,
        work_duration: float | None = None,
        work_distance_meters: float | None = None,
        work_pace: tuple[float, float] | None = None,
        work_hr_zone: int | None = None,
        rest_duration: float | None = None,
        rest_distance_meters: float | None = None,
        work_description: str = "Fast",
        rest_description: str = "Recovery",
    ) -> "RunningWorkoutBuilder":
        """Add a repeat group: *count* × (work + rest).

        Parameters
        ----------
        count:
            Number of repetitions.
        work_duration / work_distance_meters:
            End condition for the work interval.
        work_pace:
            ``(min_sec_per_km, max_sec_per_km)`` pace zone for the work interval.
        work_hr_zone:
            Heart-rate zone for the work interval (1–5).
        rest_duration / rest_distance_meters:
            End condition for the rest interval.
        """
        work_target = _make_target(work_pace, work_hr_zone)
        work_step = S.interval_step(
            duration_seconds=work_duration,
            distance_meters=work_distance_meters,
            target=work_target,
            description=work_description,
            step_order=1,
        )
        rest_step = S.rest_step(
            duration_seconds=rest_duration,
            description=rest_description,
            step_order=2,
        )
        if rest_distance_meters is not None and rest_duration is None:
            rest_step = S.interval_step(
                distance_meters=rest_distance_meters,
                description=rest_description,
                step_order=2,
            )

        group = S.repeat_group(
            sets=count,
            steps=[work_step, rest_step],
            step_order=len(self._steps) + 1,
        )
        self._steps.append(group)
        return self

    def add_raw_step(self, step: S.Step) -> "RunningWorkoutBuilder":
        """Append a pre-built step dict."""
        self._steps.append({**step, "stepOrder": len(self._steps) + 1})
        return self

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self, *, validate: bool = True) -> dict[str, Any]:
        """Return the workout payload as a JSON-serialisable dict.

        Raises
        ------
        StepLimitExceededError
            If the workout exceeds 50 steps.
        """
        if validate:
            total = S.count_steps(self._steps)
            if total > StepLimitExceededError.MAX_STEPS:
                raise StepLimitExceededError(total)

        renumbered = [{**s, "stepOrder": i + 1} for i, s in enumerate(self._steps)]

        payload: dict[str, Any] = {
            "workoutName": self.name[:80],
            "sportType": _RUNNING_SPORT_TYPE,
            "workoutSegments": [
                {
                    "segmentOrder": 1,
                    "sportType": _RUNNING_SPORT_TYPE,
                    "workoutSteps": renumbered,
                }
            ],
        }
        if self.description:
            payload["description"] = self.description[:512]
        return payload

    def to_garminconnect_model(self):
        """Return a ``garminconnect.workout.RunningWorkout`` Pydantic model.

        Requires ``pip install garminconnect[workout]``.  Useful if you
        prefer the typed upload methods (``client.upload_running_workout()``).
        """
        try:
            from garminconnect.workout import RunningWorkout, WorkoutSegment
        except ImportError as exc:
            raise ImportError(
                "Install the workout extra: pip install garminconnect[workout]"
            ) from exc
        payload = self.build(validate=True)
        return RunningWorkout(**payload)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _make_target(
    pace_range: tuple[float, float] | None,
    hr_zone: int | None,
) -> dict[str, Any]:
    if pace_range is not None and hr_zone is not None:
        raise ValueError("Provide either pace_range or hr_zone, not both.")
    if pace_range is not None:
        return S.pace_zone_target(*pace_range)
    if hr_zone is not None:
        return S.heart_rate_zone_target(hr_zone)
    return S.no_target()
