"""
Server-side Garmin SSO login and OAuth ticket exchange.

login_with_credentials() uses the web SSO form at sso.garmin.com/sso/embed
(NOT the blocked /mobile/api/login endpoint) to obtain an SSO ticket, then
exchanges it for OAuth1 + OAuth2 tokens.
"""
import re
import time
from urllib.parse import parse_qs

import requests
from requests_oauthlib import OAuth1Session

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
SSO_EMBED_URL = (
    "https://sso.garmin.com/sso/embed"
    "?id=gauth-widget&embedWidget=true"
    "&gauthHost=https://sso.garmin.com/sso"
    "&clientId=GarminConnect&locale=en_US"
    "&redirectAfterAccountLoginUrl=https://sso.garmin.com/sso/embed"
    "&service=https://sso.garmin.com/sso/embed"
)

OAUTH_CONSUMER_URL = "https://thegarth.s3.amazonaws.com/oauth_consumer.json"
ANDROID_UA = "com.garmin.android.apps.connectmobile"

_consumer_cache: dict | None = None


def browser_login(email: str = "", password: str = "") -> tuple[dict, dict]:
    """
    Login via a headed Playwright browser window.
    Pre-fills credentials if provided; the user can complete MFA manually.
    Returns (oauth1, oauth2) token dicts.
    """
    import logging
    import time
    from playwright.sync_api import sync_playwright

    logger = logging.getLogger(__name__)
    ticket = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_context(user_agent=BROWSER_UA, locale="en-US").new_page()
        page.goto(SSO_EMBED_URL, wait_until="domcontentloaded", timeout=20_000)

        if email and password:
            try:
                page.wait_for_selector('input[name="username"]', timeout=10_000)
                page.fill('input[name="username"]', email)
                page.fill('input[name="password"]', password)
                page.click('button[type="submit"], input[type="submit"]')
            except Exception:
                pass  # user can complete login manually if auto-fill fails

        deadline = time.time() + 300  # 5-minute window
        while time.time() < deadline:
            try:
                for src in [page.url]:
                    m = re.search(r"ticket=(ST-[A-Za-z0-9\-]+)", src)
                    if m:
                        ticket = m.group(1)
                        break
                if not ticket:
                    try:
                        content = page.content()
                        m = re.search(r"serviceTicket['\"]?\s*:\s*['\"]?(ST-[A-Za-z0-9\-]+)", content)
                        if m:
                            ticket = m.group(1)
                    except Exception:
                        pass
            except Exception:
                pass
            if ticket:
                break
            page.wait_for_timeout(500)

        browser.close()

    if not ticket:
        raise ValueError("Login timed out or was cancelled.")

    logger.info("Got SSO ticket: %s...", ticket[:20])
    oauth1, oauth2 = exchange_ticket(ticket)
    logger.info("Tokens exchanged successfully.")
    return oauth1, oauth2


def make_token_b64(oauth1: dict, oauth2: dict) -> str:
    """Encode tokens in the format garth's loads() expects: base64([oauth1, oauth2])."""
    import base64 as _b64
    import json as _json
    return _b64.b64encode(_json.dumps([oauth1, oauth2]).encode()).decode()


def get_consumer() -> dict:
    global _consumer_cache
    if _consumer_cache is None:
        resp = requests.get(OAUTH_CONSUMER_URL, timeout=10)
        resp.raise_for_status()
        _consumer_cache = resp.json()
    return _consumer_cache


def exchange_ticket(ticket: str) -> tuple[dict, dict]:
    """Exchange an SSO ticket for (oauth1, oauth2) token dicts."""
    consumer = get_consumer()

    # Step 1: ticket → OAuth1 (retry up to 3 times on 429)
    sess = OAuth1Session(consumer["consumer_key"], consumer["consumer_secret"])
    for attempt in range(3):
        r1 = sess.get(
            "https://connectapi.garmin.com/oauth-service/oauth/preauthorized"
            f"?ticket={ticket}"
            "&login-url=https://sso.garmin.com/sso/embed"
            "&accepts-mfa-tokens=true",
            headers={"User-Agent": ANDROID_UA},
            timeout=15,
        )
        if r1.status_code != 429:
            break
        if attempt < 2:
            time.sleep(5 * (attempt + 1))
    r1.raise_for_status()
    raw1 = {k: v[0] for k, v in parse_qs(r1.text).items()}
    # garth's OAuth1Token accepts exactly these fields
    oauth1 = {
        "oauth_token": raw1["oauth_token"],
        "oauth_token_secret": raw1["oauth_token_secret"],
        "domain": "garmin.com",
        "mfa_token": raw1.get("mfa_token"),
        "mfa_expiration_timestamp": raw1.get("mfa_expiration_timestamp"),
    }

    # Step 2: OAuth1 → OAuth2
    sess2 = OAuth1Session(
        consumer["consumer_key"],
        consumer["consumer_secret"],
        resource_owner_key=oauth1["oauth_token"],
        resource_owner_secret=oauth1["oauth_token_secret"],
    )
    data = {"mfa_token": oauth1["mfa_token"]} if oauth1.get("mfa_token") else {}
    r2 = sess2.post(
        "https://connectapi.garmin.com/oauth-service/oauth/exchange/user/2.0",
        headers={"User-Agent": ANDROID_UA, "Content-Type": "application/x-www-form-urlencoded"},
        data=data,
        timeout=15,
    )
    r2.raise_for_status()
    raw2 = r2.json()
    now = int(time.time())
    # garth's OAuth2Token only accepts these fields
    oauth2 = {
        "scope": raw2.get("scope", ""),
        "jti": raw2.get("jti", ""),
        "token_type": raw2.get("token_type", "Bearer"),
        "access_token": raw2["access_token"],
        "refresh_token": raw2["refresh_token"],
        "expires_in": int(raw2["expires_in"]),
        "expires_at": now + int(raw2["expires_in"]),
        "refresh_token_expires_in": int(raw2["refresh_token_expires_in"]),
        "refresh_token_expires_at": now + int(raw2["refresh_token_expires_in"]),
    }

    return oauth1, oauth2
