"""
GarminForgeClient — the main entry point for interacting with Garmin Connect.

Responsibilities
----------------
1. Lifecycle management of the underlying ``garminconnect.Garmin`` instance.
   Tokens are loaded once; the client is reused for all API calls.
2. Unified upload methods for all workout types (strength via raw JSON,
   endurance via either raw JSON or the typed ``garminconnect.workout`` models).
3. Transparent retry / back-off on rate-limit (429) and transient network errors.
4. Thin wrappers around common read operations (list workouts, get single
   workout, delete workout, schedule workout).

Typical usage::

    from garminforge.client import GarminForgeClient
    from garminforge.auth import TokenStore
    from garminforge.workouts.strength import StrengthWorkout, ExerciseBlock

    client = GarminForgeClient(TokenStore())

    workout = (
        StrengthWorkout("Leg Day")
        .add_warmup(description="5 min warm-up")
        .add_block(ExerciseBlock("SQUAT", "BARBELL_BACK_SQUAT", sets=4, reps=5, rest_seconds=180))
        .add_block(ExerciseBlock("LEG_CURL", "LYING_LEG_CURL", sets=3, reps=12, rest_seconds=90))
        .add_cooldown()
    )

    result = client.upload_workout(workout.build())
    workout_id = result["workoutId"]
    client.schedule_workout(workout_id, "2026-04-07")
"""

from __future__ import annotations

import logging
import time
from typing import Any

from garminconnect import Garmin

from garminforge.auth import TokenStore, load_client, with_backoff, _garth
from garminforge.exceptions import AuthenticationError, TooManyRequestsError

logger = logging.getLogger(__name__)

# Seconds to pause between consecutive API calls to respect undocumented
# rate limits.  Set to 0 to disable.
DEFAULT_INTER_CALL_DELAY: float = 1.0

# Endpoint constants (relative to the Garmin Connect base URL).
_WORKOUT_ENDPOINT = "/workout-service/workout"
_WORKOUTS_ENDPOINT = "/workout-service/workouts"


class GarminForgeClient:
    """Authenticated Garmin Connect client with workout management helpers.

    Parameters
    ----------
    store:
        Token storage strategy (file path or base64 string).  Defaults to
        ``~/.garminconnect`` (or the ``GARMINTOKENS`` env var).
    inter_call_delay:
        Seconds to sleep between consecutive API calls.  Defaults to 1.0.
    """

    def __init__(
        self,
        store: TokenStore | None = None,
        inter_call_delay: float = DEFAULT_INTER_CALL_DELAY,
    ) -> None:
        self._store = store or TokenStore()
        self._delay = inter_call_delay
        self._garmin: Garmin | None = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    @property
    def garmin(self) -> Garmin:
        """Lazily initialise and return the authenticated ``Garmin`` client."""
        if self._garmin is None:
            self._garmin = load_client(self._store)
            logger.info("Garmin Connect client initialised from token store.")
        return self._garmin

    def refresh_tokens(self) -> None:
        """Force a token refresh (load from store again).

        Call this if you receive ``AuthenticationError`` from an API call and
        believe tokens have been rotated externally.
        """
        self._garmin = load_client(self._store)

    # ------------------------------------------------------------------
    # Workout CRUD
    # ------------------------------------------------------------------

    def upload_workout(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Upload a workout and return the server response (includes ``workoutId``).

        Accepts any sport type — strength, running, cycling, etc.  *payload*
        must conform to Garmin's workout JSON schema (see workouts/ builders).

        Parameters
        ----------
        payload:
            JSON-serialisable workout dict, e.g. from ``StrengthWorkout.build()``
            or ``RunningWorkoutBuilder.build()``.
        """
        return self._call(
            _garth(self.garmin).connectapi,
            _WORKOUT_ENDPOINT,
            method="POST",
            json=payload,
        )

    def get_workout(self, workout_id: int | str) -> dict[str, Any]:
        """Fetch a single workout by ID."""
        return self._call(
            _garth(self.garmin).connectapi,
            f"{_WORKOUT_ENDPOINT}/{workout_id}",
        )

    def get_workouts(
        self,
        start: int = 0,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Return a paginated list of saved workouts (most recent first).

        Parameters
        ----------
        start:
            Zero-based offset for pagination.
        limit:
            Number of workouts to return (max ~100 per call).
        """
        return self._call(
            _garth(self.garmin).connectapi,
            _WORKOUTS_ENDPOINT,
            params={"start": start, "limit": limit},
        )

    def delete_workout(self, workout_id: int | str) -> None:
        """Delete a workout by ID.

        This is irreversible; the workout is removed from Garmin Connect
        permanently.
        """
        self._call(
            _garth(self.garmin).connectapi,
            f"{_WORKOUT_ENDPOINT}/{workout_id}",
            method="DELETE",
        )
        logger.info("Deleted workout %s.", workout_id)

    def schedule_workout(
        self,
        workout_id: int | str,
        date: str,
    ) -> dict[str, Any]:
        """Assign a workout to a calendar date.

        Parameters
        ----------
        workout_id:
            The ``workoutId`` returned by ``upload_workout``.
        date:
            ISO 8601 date string, e.g. ``"2026-04-10"``.
        """
        return self._call(
            _garth(self.garmin).connectapi,
            f"/workout-service/schedule/{workout_id}",
            method="POST",
            json={"date": date},
        )

    def upload_and_schedule(
        self,
        payload: dict[str, Any],
        date: str,
    ) -> dict[str, Any]:
        """Upload a workout and immediately schedule it to *date*.

        Returns the schedule response.
        """
        upload_result = self.upload_workout(payload)
        workout_id = upload_result["workoutId"]
        logger.info("Uploaded workout %s (%r).", workout_id, payload.get("workoutName"))
        self._sleep()
        return self.schedule_workout(workout_id, date)

    # ------------------------------------------------------------------
    # Convenience read methods
    # ------------------------------------------------------------------

    def get_activities(self, start: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        """Return a list of recent activities."""
        return self._call(
            self.garmin.get_activities,
            start,
            limit,
        )

    def get_user_profile(self) -> dict[str, Any]:
        """Return the authenticated user's Garmin Connect profile."""
        return self._call(self.garmin.get_user_profile)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call(self, func, *args, **kwargs) -> Any:
        """Execute *func* with rate-limit backoff and inter-call delay."""
        result = with_backoff(func, *args, **kwargs)
        self._sleep()
        return result

    def _sleep(self) -> None:
        if self._delay > 0:
            time.sleep(self._delay)


# ---------------------------------------------------------------------------
# Module-level convenience factory
# ---------------------------------------------------------------------------


def from_token_string(token_b64: str) -> GarminForgeClient:
    """Create a ``GarminForgeClient`` from a base64 token string.

    Suitable for cloud/serverless environments where tokens are stored in
    environment variables or a secrets manager.

    Parameters
    ----------
    token_b64:
        The base64-encoded string produced by ``garth.dumps()`` or
        ``TokenStore.token_string``.
    """
    return GarminForgeClient(TokenStore(token_string=token_b64))


def from_token_dir(path: str) -> GarminForgeClient:
    """Create a ``GarminForgeClient`` loading tokens from a directory path."""
    return GarminForgeClient(TokenStore(path=path))
