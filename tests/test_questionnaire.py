"""
Tests for /my/questionnaire redirect behaviour.

The questionnaire has moved to /onboarding.  These routes now simply
redirect callers to the new location — no auth required, no DB access.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from web.app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


class TestQuestionnaireRedirects:
    def test_get_questionnaire_redirects_to_onboarding(self, client):
        resp = client.get("/my/questionnaire", follow_redirects=False)
        assert resp.status_code == 301
        assert resp.headers["location"] in ("/onboarding", "http://testserver/onboarding")

    def test_post_questionnaire_redirects_to_onboarding(self, client):
        resp = client.post("/my/questionnaire", follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] in ("/onboarding", "http://testserver/onboarding")

    def test_skip_endpoint_gone(self, client):
        """POST /my/questionnaire/skip was removed; expect 404 or 405."""
        resp = client.post("/my/questionnaire/skip", follow_redirects=False)
        assert resp.status_code in (404, 405)
