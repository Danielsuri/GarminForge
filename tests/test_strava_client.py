"""Tests for web.strava_client."""
from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch

import pytest

from garminforge.exceptions import StravaAuthError, StravaRateLimitError
from web.strava_client import StravaClient, StravaToken, strava_client_from_user


def test_token_roundtrip() -> None:
    token = StravaToken(
        access_token="abc123",
        refresh_token="ref456",
        expires_at=9999999999,
    )
    assert StravaToken.from_dict(token.as_dict()) == token


def test_token_from_dict_defaults_token_type() -> None:
    d = {"access_token": "a", "refresh_token": "r", "expires_at": 1}
    token = StravaToken.from_dict(d)
    assert token.token_type == "Bearer"


def _make_client(expires_at: int | None = None) -> StravaClient:
    if expires_at is None:
        expires_at = int(time.time()) + 7200
    token = StravaToken("acc", "ref", expires_at)
    return StravaClient(token, client_id="cid", client_secret="csec")


def test_maybe_refresh_skips_when_not_expired() -> None:
    client = _make_client(expires_at=int(time.time()) + 7200)
    with patch.object(client, "_do_refresh") as mock_refresh:
        refreshed = client._maybe_refresh()
    assert refreshed is False
    mock_refresh.assert_not_called()


def test_maybe_refresh_calls_when_expiring_soon() -> None:
    client = _make_client(expires_at=int(time.time()) + 100)
    new_token_data = {
        "access_token": "new_acc",
        "refresh_token": "new_ref",
        "expires_at": int(time.time()) + 21600,
        "token_type": "Bearer",
    }
    with patch.object(client, "_do_refresh", return_value=new_token_data) as mock_refresh:
        refreshed = client._maybe_refresh()
    assert refreshed is True
    assert client.token.access_token == "new_acc"
    mock_refresh.assert_called_once()


def test_call_raises_strava_auth_error_on_401() -> None:
    client = _make_client()
    mock_response = MagicMock()
    mock_response.status_code = 401
    with patch("httpx.Client") as mock_httpx:
        mock_httpx.return_value.__enter__.return_value.request.return_value = mock_response
        with pytest.raises(StravaAuthError):
            client._call("GET", "/athlete")


def test_call_raises_strava_rate_limit_error_on_429() -> None:
    client = _make_client()
    mock_response = MagicMock()
    mock_response.status_code = 429
    with patch("httpx.Client") as mock_httpx:
        mock_httpx.return_value.__enter__.return_value.request.return_value = mock_response
        with pytest.raises(StravaRateLimitError):
            client._call("GET", "/athlete")


def test_call_returns_json_on_200() -> None:
    client = _make_client()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": 123, "username": "testuser"}
    with patch("httpx.Client") as mock_httpx:
        mock_httpx.return_value.__enter__.return_value.request.return_value = mock_response
        result = client._call("GET", "/athlete")
    assert result == {"id": 123, "username": "testuser"}


def test_strava_client_from_user() -> None:
    user = MagicMock()
    user.strava_token_json = json.dumps({
        "access_token": "acc",
        "refresh_token": "ref",
        "expires_at": 9999999999,
        "token_type": "Bearer",
    })
    client = strava_client_from_user(user, client_id="cid", client_secret="csec")
    assert isinstance(client, StravaClient)
    assert client.token.access_token == "acc"
    assert client.client_id == "cid"


def test_call_retries_on_5xx() -> None:
    client = _make_client()
    error_response = MagicMock()
    error_response.status_code = 503
    success_response = MagicMock()
    success_response.status_code = 200
    success_response.json.return_value = {"id": 1}
    with patch("httpx.Client") as mock_httpx:
        mock_httpx.return_value.__enter__.return_value.request.side_effect = [
            error_response,
            success_response,
        ]
        result = client._call("GET", "/athlete")
    assert result == {"id": 1}
