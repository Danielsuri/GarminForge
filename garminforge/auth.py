"""
GarminForge authentication and token management.

Design principles (derived from garth/garminconnect constraints):
- Tokens last ~1 year; **never** call login() per request.
- Fresh logins have been broken since Garmin's March 2026 auth change.
  Generate tokens interactively on a local machine, then transfer them.
- Two storage strategies are supported:
    1. Directory  — two JSON files (oauth1_token.json, oauth2_token.json)
    2. Base64 string — serialised with garth.dumps() / garth.loads()
       Suitable for env vars, databases, or secrets managers.
- The ``TokenStore`` class abstracts both strategies and provides a single
  ``load()`` / ``save()`` interface used by ``GarminForgeClient``.
"""

from __future__ import annotations

import os
import time
import logging
from pathlib import Path
from typing import Callable

from garminconnect import Garmin, GarminConnectAuthenticationError
from garth.exc import GarthHTTPError

from garminforge.exceptions import AuthenticationError, TokenNotFoundError

logger = logging.getLogger(__name__)

# Default token directory — override with GARMINTOKENS env var.
_DEFAULT_TOKENSTORE = Path("~/.garminconnect").expanduser()


class TokenStore:
    """Manages persistence and retrieval of Garmin OAuth tokens.

    Parameters
    ----------
    path:
        Filesystem directory containing ``oauth1_token.json`` and
        ``oauth2_token.json``.  Defaults to ``~/.garminconnect`` (or the
        ``GARMINTOKENS`` environment variable if set).
    token_string:
        A base64-encoded token blob produced by ``garth.dumps()``.  When
        provided, filesystem storage is bypassed entirely; ``save()`` updates
        this attribute in memory and returns the new string.
    """

    def __init__(
        self,
        path: str | Path | None = None,
        token_string: str | None = None,
    ) -> None:
        if token_string is not None:
            self._token_string: str | None = token_string
            self._path: Path | None = None
        else:
            raw = path or os.environ.get("GARMINTOKENS") or str(_DEFAULT_TOKENSTORE)
            self._path = Path(raw).expanduser()
            self._token_string = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def load(self, client: Garmin) -> None:
        """Populate *client*'s garth instance from stored tokens.

        Raises
        ------
        TokenNotFoundError
            If neither a token string nor a readable token directory exists.
        AuthenticationError
            If the stored tokens are present but rejected by Garmin.
        """
        try:
            if self._token_string is not None:
                client.garth.loads(self._token_string)
                logger.debug("Loaded tokens from base64 string.")
            else:
                assert self._path is not None
                if not self._path.exists():
                    raise TokenNotFoundError(
                        f"Token directory not found: {self._path}.  "
                        "Run interactive_login() on a local machine first."
                    )
                client.login(str(self._path))
                logger.debug("Loaded tokens from %s.", self._path)
        except GarminConnectAuthenticationError as exc:
            raise AuthenticationError(
                "Stored tokens were rejected by Garmin Connect.  "
                "They may have expired.  Re-generate via interactive_login()."
            ) from exc
        except GarthHTTPError as exc:
            raise AuthenticationError(str(exc)) from exc

    def save(self, client: Garmin) -> str | None:
        """Persist tokens from *client*'s garth instance.

        Returns the base64 token string when operating in string mode,
        otherwise writes files to disk and returns ``None``.
        """
        if self._token_string is not None:
            self._token_string = client.garth.dumps()
            logger.debug("Updated in-memory token string.")
            return self._token_string

        assert self._path is not None
        self._path.mkdir(mode=0o700, parents=True, exist_ok=True)
        client.garth.dump(str(self._path))
        # Tighten file permissions.
        for f in self._path.glob("*.json"):
            f.chmod(0o600)
        logger.debug("Saved tokens to %s.", self._path)
        return None

    @property
    def token_string(self) -> str | None:
        """Current base64 token string, or ``None`` if using file storage."""
        return self._token_string


# ---------------------------------------------------------------------------
# Interactive / headless login helpers
# ---------------------------------------------------------------------------


def interactive_login(
    email: str,
    password: str,
    store: TokenStore | None = None,
    prompt_mfa: Callable[[], str] | None = None,
) -> tuple[Garmin, TokenStore]:
    """Perform a full interactive login and persist the resulting tokens.

    Because Garmin's SSO broke in March 2026, this function may fail for
    new accounts.  Prefer transferring tokens from an environment where
    authentication still works.

    Parameters
    ----------
    email:
        Garmin Connect account e-mail.
    password:
        Account password.
    store:
        Where to save the resulting tokens.  Defaults to ``~/.garminconnect``.
    prompt_mfa:
        Callable that returns the MFA/OTP code when invoked.
        Defaults to ``lambda: input("MFA code: ")``.

    Returns
    -------
    (client, store)
        The authenticated ``Garmin`` instance and the ``TokenStore`` used.
    """
    store = store or TokenStore()
    mfa_callback = prompt_mfa or (lambda: input("MFA code: "))

    client = Garmin(email=email, password=password, return_on_mfa=True)
    try:
        result = client.login()
    except GarminConnectAuthenticationError as exc:
        raise AuthenticationError(
            "Login failed.  Garmin's SSO has been broken since March 2026; "
            "fresh logins may not work.  See garth issue #217."
        ) from exc

    if isinstance(result, tuple) and result[0] == "needs_mfa":
        mfa_code = mfa_callback()
        client.resume_login(result[1], mfa_code)

    store.save(client)
    logger.info("Login successful; tokens saved.")
    return client, store


def load_client(store: TokenStore | None = None) -> Garmin:
    """Return an authenticated ``Garmin`` client using persisted tokens.

    Parameters
    ----------
    store:
        Token store to load from.  Defaults to ``~/.garminconnect`` (or
        ``GARMINTOKENS`` env var).

    Raises
    ------
    TokenNotFoundError
        If no tokens are found.
    AuthenticationError
        If tokens are present but invalid.
    """
    store = store or TokenStore()
    client = Garmin()
    store.load(client)
    return client


# ---------------------------------------------------------------------------
# Retry decorator (used by client.py)
# ---------------------------------------------------------------------------


def with_backoff(
    func: Callable,
    *args,
    retries: int = 4,
    base_delay: float = 2.0,
    **kwargs,
):
    """Call *func* with exponential backoff on transient errors.

    Retries on ``GarminConnectTooManyRequestsError`` and network errors;
    re-raises immediately on auth errors.
    """
    from garminconnect import (
        GarminConnectTooManyRequestsError,
        GarminConnectConnectionError,
    )

    delay = base_delay
    for attempt in range(retries + 1):
        try:
            return func(*args, **kwargs)
        except GarminConnectAuthenticationError as exc:
            raise AuthenticationError(str(exc)) from exc
        except GarminConnectTooManyRequestsError as exc:
            if attempt == retries:
                raise
            wait = delay * (2 ** attempt)
            logger.warning("Rate limited (429); retrying in %.0fs…", wait)
            time.sleep(wait)
        except GarminConnectConnectionError as exc:
            if attempt == retries:
                from garminforge.exceptions import ConnectionError as ForgeConnErr
                raise ForgeConnErr(str(exc)) from exc
            wait = delay * (2 ** attempt)
            logger.warning("Connection error; retrying in %.0fs…", wait)
            time.sleep(wait)
