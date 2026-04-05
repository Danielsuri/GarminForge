"""
Regression tests for the questionnaire wizard template.
Verifies that the rendered HTML contains all form field names
the backend handler expects — guarding against accidental renames.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from web.app import app
from web.models import User


def _make_user() -> User:
    return User(
        id="test-qx-001",
        email="wizard@test.com",
        questionnaire_completed=False,
        age=None,
        diet_json=None,
        health_conditions_json=None,
        preferred_equipment_json=None,
        fitness_level=None,
        fitness_goals_json=None,
        weekly_workout_days=None,
    )


@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


class TestQuestionnaireTemplate:
    def _get_page(self, client):
        user = _make_user()
        with patch("web.routes_my.get_current_user", return_value=user):
            return client.get("/my/questionnaire")

    def test_returns_200(self, client):
        assert self._get_page(client).status_code == 200

    def test_has_age_field(self, client):
        assert 'name="age"' in self._get_page(client).text

    def test_has_fitness_level_field(self, client):
        assert 'name="fitness_level"' in self._get_page(client).text

    def test_has_weekly_workout_days_field(self, client):
        assert 'name="weekly_workout_days"' in self._get_page(client).text

    def test_has_fitness_goals_field(self, client):
        assert 'name="fitness_goals"' in self._get_page(client).text

    def test_has_equipment_field(self, client):
        assert 'name="equipment"' in self._get_page(client).text

    def test_has_diet_field(self, client):
        assert 'name="diet"' in self._get_page(client).text

    def test_has_health_conditions_field(self, client):
        assert 'name="health_conditions"' in self._get_page(client).text

    def test_form_posts_to_questionnaire(self, client):
        assert 'action="/my/questionnaire"' in self._get_page(client).text

    def test_skip_posts_to_skip_route(self, client):
        assert 'action="/my/questionnaire/skip"' in self._get_page(client).text

    def test_seven_wcard_elements(self, client):
        """One card per question (not counting summary)."""
        html = self._get_page(client).text
        assert html.count('class="wcard') >= 7
