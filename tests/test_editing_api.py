"""
HTTP-level integration tests for the workout editing API endpoints:
  GET  /workout/exercises
  POST /workout/rebuild
  POST /workout/upload  (redirect on success, error paths)

Uses FastAPI's TestClient — no running server required.
"""

from __future__ import annotations

import dataclasses
import json

import pytest
from fastapi.testclient import TestClient

from web.app import app
from web.workout_generator import GOALS, generate


@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture(scope="module")
def sample_exercises():
    plan = generate(["bodyweight"], "build_muscle", 45, seed=42)
    return [dataclasses.asdict(e) for e in plan.exercises]


# ---------------------------------------------------------------------------
# GET /workout/exercises
# ---------------------------------------------------------------------------


class TestExercisesEndpoint:
    def test_returns_200_with_list(self, client):
        resp = client.get("/workout/exercises?goal=build_muscle")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) > 0

    def test_each_item_has_required_fields(self, client):
        resp = client.get("/workout/exercises?goal=build_muscle&equipment=bodyweight")
        required = {"category", "name", "label", "muscle_group"}
        for item in resp.json():
            assert required <= item.keys()

    def test_equipment_filter(self, client):
        bw = client.get("/workout/exercises?goal=build_muscle&equipment=bodyweight")
        with_barbell = client.get(
            "/workout/exercises?goal=build_muscle&equipment=bodyweight&equipment=barbell"
        )
        assert len(with_barbell.json()) > len(bw.json())

    def test_muscle_group_filter(self, client):
        resp = client.get(
            "/workout/exercises?goal=build_muscle&equipment=bodyweight&muscle_group=push"
        )
        assert resp.status_code == 200
        assert all(ex["muscle_group"] == "push" for ex in resp.json())

    def test_exclude_param_removes_exercise(self, client):
        resp = client.get(
            "/workout/exercises?goal=build_muscle&equipment=bodyweight&muscle_group=push"
        )
        items = resp.json()
        if not items:
            pytest.skip("No push/bodyweight exercises")
        name = items[0]["name"]
        resp2 = client.get(
            f"/workout/exercises?goal=build_muscle&equipment=bodyweight"
            f"&muscle_group=push&exclude={name}"
        )
        assert all(ex["name"] != name for ex in resp2.json())

    def test_unknown_goal_returns_400(self, client):
        resp = client.get("/workout/exercises?goal=definitely_not_a_goal")
        assert resp.status_code == 400
        assert "error" in resp.json()

    def test_goal_required(self, client):
        resp = client.get("/workout/exercises")
        assert resp.status_code == 422  # FastAPI validation error

    @pytest.mark.parametrize("goal", list(GOALS))
    def test_all_goals_return_results(self, client, goal):
        resp = client.get(f"/workout/exercises?goal={goal}")
        assert resp.status_code == 200
        assert len(resp.json()) > 0


# ---------------------------------------------------------------------------
# POST /workout/rebuild
# ---------------------------------------------------------------------------


class TestRebuildEndpoint:
    def test_returns_payload_json_string(self, client, sample_exercises):
        resp = client.post(
            "/workout/rebuild",
            json={
                "exercises": sample_exercises,
                "goal": "build_muscle",
                "duration_minutes": 45,
                "workout_name": "Test Workout",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "payload_json" in data
        # payload_json must be valid JSON
        payload = json.loads(data["payload_json"])
        assert payload["workoutName"] == "Test Workout"

    def test_payload_has_strength_sport_type(self, client, sample_exercises):
        resp = client.post(
            "/workout/rebuild",
            json={
                "exercises": sample_exercises,
                "goal": "build_muscle",
                "duration_minutes": 45,
                "workout_name": "Test",
            },
        )
        payload = json.loads(resp.json()["payload_json"])
        assert payload["sportType"]["sportTypeId"] == 5

    def test_unknown_goal_returns_400(self, client, sample_exercises):
        resp = client.post(
            "/workout/rebuild",
            json={
                "exercises": sample_exercises,
                "goal": "not_real",
                "duration_minutes": 45,
                "workout_name": "Test",
            },
        )
        assert resp.status_code == 400
        assert "error" in resp.json()

    def test_empty_exercises_returns_400(self, client):
        resp = client.post(
            "/workout/rebuild",
            json={
                "exercises": [],
                "goal": "build_muscle",
                "duration_minutes": 45,
                "workout_name": "Test",
            },
        )
        assert resp.status_code == 400

    def test_invalid_json_body_returns_400(self, client):
        resp = client.post(
            "/workout/rebuild",
            content=b"not json at all",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400

    @pytest.mark.parametrize("goal", list(GOALS))
    def test_all_goals_rebuild_successfully(self, client, goal):
        plan = generate(["bodyweight"], goal, 45, seed=42)
        exercises = [dataclasses.asdict(e) for e in plan.exercises]
        resp = client.post(
            "/workout/rebuild",
            json={
                "exercises": exercises,
                "goal": goal,
                "duration_minutes": 45,
                "workout_name": "Test",
            },
        )
        assert resp.status_code == 200, f"goal={goal!r}: {resp.json()}"
        payload = json.loads(resp.json()["payload_json"])
        assert "workoutSegments" in payload

    def test_single_exercise_ok(self, client, sample_exercises):
        resp = client.post(
            "/workout/rebuild",
            json={
                "exercises": sample_exercises[:1],
                "goal": "build_muscle",
                "duration_minutes": 30,
                "workout_name": "Solo",
            },
        )
        assert resp.status_code == 200

    def test_exercise_order_preserved_in_payload(self, client, sample_exercises):
        reversed_ex = list(reversed(sample_exercises))
        resp = client.post(
            "/workout/rebuild",
            json={
                "exercises": reversed_ex,
                "goal": "build_muscle",
                "duration_minutes": 45,
                "workout_name": "Test",
            },
        )
        payload = json.loads(resp.json()["payload_json"])
        steps = payload["workoutSegments"][0]["workoutSteps"]
        circuit = next(s for s in steps if s.get("stepType", {}).get("stepTypeKey") == "repeat")
        exercise_steps = [
            s
            for s in circuit["workoutSteps"]
            if s.get("stepType", {}).get("stepTypeKey") == "interval"
        ]
        actual = [s["exerciseName"] for s in exercise_steps]
        expected = [ex["name"].upper() for ex in reversed_ex]
        assert actual == expected


# ---------------------------------------------------------------------------
# POST /workout/upload (redirect path, no real Garmin connection needed)
# ---------------------------------------------------------------------------


class TestUploadEndpoint:
    def test_unauthenticated_redirects_with_error(self, client):
        resp = client.post(
            "/workout/upload",
            data={"payload_json": json.dumps({"workoutName": "Test"})},
            follow_redirects=False,
        )
        # Should redirect (303) to error path when not authenticated
        assert resp.status_code == 303

    def test_invalid_payload_json_redirects_with_error(self, client):
        resp = client.post(
            "/workout/upload",
            data={"payload_json": "not valid json {{{}"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
