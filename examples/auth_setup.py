"""
Example: first-time authentication and token management.

Run this interactively on a local machine to generate OAuth tokens.
Transfer ~/.garminconnect to any server/environment where you need
headless access.

    python examples/auth_setup.py

IMPORTANT: Garmin's SSO broke in March 2026.  Fresh logins may fail.
           If they do, watch garth issue #217 and python-garminconnect
           issues #332 / #337 for updates.
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO)

from garminforge.auth import interactive_login, TokenStore
from garminforge.exceptions import AuthenticationError


def main() -> None:
    email = os.environ.get("GARMIN_EMAIL") or input("Garmin email: ").strip()
    password = os.environ.get("GARMIN_PASSWORD") or input("Garmin password: ").strip()

    # Default store: ~/.garminconnect
    # Override with GARMINTOKENS env var or pass path= to TokenStore().
    store = TokenStore()

    print("\nAttempting login …  (Garmin SSO may be broken — see module docstring)")
    try:
        client, store = interactive_login(
            email=email,
            password=password,
            store=store,
        )
    except AuthenticationError as exc:
        print(f"\nAuthentication failed: {exc}", file=sys.stderr)
        sys.exit(1)

    print("\nLogin successful!")
    print(f"Tokens saved to: {store._path or '(in-memory string)'}")

    # Show base64 token string — copy this to a secrets manager.
    b64 = client.garth.dumps()
    print(f"\nBase64 token string (store securely):\n{b64[:40]}…  ({len(b64)} chars)")

    # Verify access by fetching the user profile.
    from garminforge.client import GarminForgeClient
    forge_client = GarminForgeClient(store)
    try:
        profile = forge_client.get_user_profile()
        print(f"\nLogged in as: {profile.get('displayName', 'unknown')}")
    except Exception as exc:
        print(f"\nProfile fetch failed: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
