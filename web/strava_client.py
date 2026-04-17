"""Strava API v3 HTTP client with automatic token refresh."""

from __future__ import annotations

import json
import time
import logging
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

import httpx

from garminforge.exceptions import StravaAuthError, StravaRateLimitError

if TYPE_CHECKING:
    from web.models import User

logger = logging.getLogger(__name__)

_TOKEN_ENDPOINT = "https://www.strava.com/oauth/token"
_REFRESH_BUFFER_SECONDS = 300  # refresh 5 min before expiry


@dataclass
class StravaToken:
    """Strava OAuth2 token bundle."""

    access_token: str
    refresh_token: str
    expires_at: int  # Unix timestamp
    token_type: str = "Bearer"

    def as_dict(self) -> dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "token_type": self.token_type,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "StravaToken":
        return cls(
            access_token=d["access_token"],
            refresh_token=d["refresh_token"],
            expires_at=int(d["expires_at"]),
            token_type=d.get("token_type", "Bearer"),
        )


class StravaClient:
    """Thin wrapper around Strava API v3. Token refresh is handled transparently."""

    BASE = "https://www.strava.com/api/v3"

    def __init__(self, token: StravaToken, client_id: str, client_secret: str) -> None:
        self.token = token
        self.client_id = client_id
        self.client_secret = client_secret

    def _do_refresh(self) -> dict[str, Any]:
        """POST to Strava token endpoint to exchange refresh_token for new tokens."""
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                _TOKEN_ENDPOINT,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": self.token.refresh_token,
                },
            )
        if resp.status_code == 401:
            raise StravaAuthError("Strava refresh token is invalid or revoked.")
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]

    def _maybe_refresh(self) -> bool:
        """Refresh the access token if it expires within the buffer window.
        Updates self.token in-place. Returns True if a refresh occurred.
        """
        if self.token.expires_at > time.time() + _REFRESH_BUFFER_SECONDS:
            return False
        logger.debug("Strava access token expiring soon — refreshing.")
        data = self._do_refresh()
        self.token = StravaToken.from_dict(data)
        return True

    def _check_response(self, response: httpx.Response, method: str, path: str) -> Any:
        """Check response status and return JSON or raise typed exceptions."""
        if response.status_code == 401:
            raise StravaAuthError(f"Strava returned 401 for {method} {path}")
        if response.status_code == 429:
            raise StravaRateLimitError("Strava rate limit reached (100 req/15 min or 1 000/day).")
        response.raise_for_status()
        return response.json()

    def _call(self, method: str, path: str, **kwargs: Any) -> Any:
        """Make an authenticated request; raise typed exceptions on error.
        Retries once on transient 5xx responses.
        """
        self._maybe_refresh()
        headers = {"Authorization": f"Bearer {self.token.access_token}"}
        url = self.BASE + path

        with httpx.Client(timeout=20) as client:
            response = client.request(method, url, headers=headers, **kwargs)

        if response.status_code >= 500 and method.upper() == "GET":
            # One retry on server errors (GET only — POST is not idempotent)
            with httpx.Client(timeout=20) as client:
                response = client.request(method, url, headers=headers, **kwargs)

        return self._check_response(response, method, path)

    def get_athlete(self) -> dict[str, Any]:
        """Return the authenticated athlete profile."""
        return self._call("GET", "/athlete")  # type: ignore[no-any-return]

    def list_activities(self, days_back: int = 90) -> list[dict[str, Any]]:
        """Return up to 200 activities from the past days_back days."""
        after = int(time.time()) - days_back * 86400
        return self._call(  # type: ignore[no-any-return]
            "GET",
            "/athlete/activities",
            params={"after": after, "per_page": 200},
        )

    def create_activity(
        self,
        name: str,
        sport_type: str,
        start_date_local: str,
        elapsed_time: int,
        description: str = "",
    ) -> dict[str, Any]:
        """Manually create an activity."""
        return self._call(  # type: ignore[no-any-return]
            "POST",
            "/activities",
            data={
                "name": name,
                "sport_type": sport_type,
                "start_date_local": start_date_local,
                "elapsed_time": elapsed_time,
                "description": description,
            },
        )


def strava_client_from_user(
    user: "User",
    client_id: str,
    client_secret: str,
) -> StravaClient:
    """Construct a StravaClient from a User ORM instance."""
    if not user.strava_token_json:
        raise StravaAuthError("User has no Strava token. Reconnect via /strava/connect.")
    token = StravaToken.from_dict(json.loads(user.strava_token_json))
    return StravaClient(token, client_id=client_id, client_secret=client_secret)
