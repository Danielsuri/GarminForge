"""
GarminForge exceptions.

Wraps garminconnect and garth exceptions with additional context, and defines
forge-specific errors for workout validation.
"""

from __future__ import annotations


class GarminForgeError(Exception):
    """Base exception for all GarminForge errors."""


# ---------------------------------------------------------------------------
# Auth / connectivity
# ---------------------------------------------------------------------------


class AuthenticationError(GarminForgeError):
    """Raised when Garmin Connect authentication fails or tokens are expired.

    Recovery: generate fresh tokens interactively on a local machine, then
    copy them to the target environment (see auth.py).
    """


class TokenNotFoundError(AuthenticationError):
    """Raised when no saved tokens exist at the expected path."""


class TooManyRequestsError(GarminForgeError):
    """Raised when Garmin's rate limiter returns HTTP 429.

    Back off for at least 60 seconds before retrying.
    """


class ConnectionError(GarminForgeError):  # noqa: A001 — intentional shadowing
    """Raised on network errors or unexpected 4xx/5xx responses."""


# ---------------------------------------------------------------------------
# Workout validation
# ---------------------------------------------------------------------------


class WorkoutValidationError(GarminForgeError):
    """Raised when a workout fails pre-upload validation."""


class StepLimitExceededError(WorkoutValidationError):
    """Raised when a workout exceeds Garmin's 50-step limit."""

    MAX_STEPS = 50

    def __init__(self, count: int) -> None:
        super().__init__(
            f"Workout has {count} steps; Garmin Connect enforces a maximum of "
            f"{self.MAX_STEPS}.  Split the workout or use a FIT file instead."
        )


class UnknownExerciseError(WorkoutValidationError):
    """Raised when an unrecognised exerciseCategory/exerciseName pair is used."""

    def __init__(self, category: str, name: str) -> None:
        super().__init__(
            f"Unknown exercise: category={category!r}, name={name!r}.  "
            "Check garminforge.workouts.exercises for the full catalog."
        )
