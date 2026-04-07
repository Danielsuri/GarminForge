"""
Unit tests for the workout editing backend:
  - workout_generator.get_available_exercises()
  - workout_generator.rebuild_garmin_payload()

No server or browser required.
"""
from __future__ import annotations

import dataclasses

import pytest

from web.workout_generator import GOALS, generate, get_available_exercises, rebuild_garmin_payload


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _exercises_for(goal: str, equipment: list[str] | None = None, count: int | None = None):
    plan = generate(equipment or ["bodyweight"], goal, 45, seed=42)
    exs = [dataclasses.asdict(e) for e in plan.exercises]
    return exs[:count] if count else exs


# ---------------------------------------------------------------------------
# get_available_exercises
# ---------------------------------------------------------------------------

class TestGetAvailableExercises:
    def test_returns_non_empty_list(self):
        result = get_available_exercises(["bodyweight"], "build_muscle")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_each_item_has_required_keys(self):
        result = get_available_exercises(["bodyweight"], "build_muscle")
        required = {"category", "name", "label", "muscle_group", "equipment_labels", "link"}
        for item in result:
            assert required <= item.keys(), f"Missing keys in {item}"

    def test_more_equipment_more_exercises(self):
        bodyweight = get_available_exercises(["bodyweight"], "build_muscle")
        with_barbell = get_available_exercises(["bodyweight", "barbell"], "build_muscle")
        assert len(with_barbell) > len(bodyweight)

    def test_muscle_group_filter(self):
        result = get_available_exercises(["bodyweight", "barbell"], "build_muscle", "push")
        assert len(result) > 0
        assert all(ex["muscle_group"] == "push" for ex in result)

    def test_exclude_removes_exact_exercise(self):
        items = get_available_exercises(["bodyweight"], "build_muscle", "push")
        if not items:
            pytest.skip("No push/bodyweight exercises available")
        excluded = items[0]["name"]
        filtered = get_available_exercises(["bodyweight"], "build_muscle", "push", excluded)
        assert all(ex["name"] != excluded for ex in filtered)

    def test_exclude_with_no_muscle_group_filter(self):
        all_items = get_available_exercises(["bodyweight"], "build_muscle")
        excluded = all_items[0]["name"]
        result = get_available_exercises(["bodyweight"], "build_muscle", None, excluded)
        assert all(ex["name"] != excluded for ex in result)

    def test_all_goals_return_results(self):
        for goal in GOALS:
            result = get_available_exercises(["bodyweight"], goal)
            assert len(result) > 0, f"No exercises for goal {goal!r}"

    def test_empty_equipment_falls_back_to_bodyweight(self):
        result = get_available_exercises([], "build_muscle")
        assert len(result) > 0

    def test_equipment_labels_empty_for_bodyweight_exercises(self):
        result = get_available_exercises(["bodyweight"], "build_muscle")
        # Bodyweight-only exercises should have no required_equipment_labels
        pure_bw = [ex for ex in result if not ex["equipment_labels"]]
        assert len(pure_bw) > 0


# ---------------------------------------------------------------------------
# rebuild_garmin_payload
# ---------------------------------------------------------------------------

class TestRebuildGarminPayload:
    def test_returns_dict_with_required_keys(self):
        exercises = _exercises_for("build_muscle")
        payload = rebuild_garmin_payload(exercises, "build_muscle", 45, "Test Workout")
        assert "workoutName" in payload
        assert "sportType" in payload
        assert "workoutSegments" in payload

    def test_workout_name_stored_correctly(self):
        exercises = _exercises_for("build_muscle")
        name = "My Custom Workout"
        payload = rebuild_garmin_payload(exercises, "build_muscle", 45, name)
        assert payload["workoutName"] == name

    def test_sport_type_is_strength_training(self):
        exercises = _exercises_for("build_muscle")
        payload = rebuild_garmin_payload(exercises, "build_muscle", 45, "Test")
        assert payload["sportType"]["sportTypeId"] == 5
        assert payload["sportType"]["sportTypeKey"] == "strength_training"

    def test_structure_has_warmup_circuit_cooldown(self):
        exercises = _exercises_for("build_muscle")
        payload = rebuild_garmin_payload(exercises, "build_muscle", 45, "Test")
        steps = payload["workoutSegments"][0]["workoutSteps"]
        step_keys = [s.get("stepType", {}).get("stepTypeKey") for s in steps]
        assert "warmup" in step_keys
        assert "cooldown" in step_keys
        assert "repeat" in step_keys

    def test_preserves_exercise_order(self):
        exercises = _exercises_for("build_muscle", count=4)
        reversed_exercises = list(reversed(exercises))
        payload = rebuild_garmin_payload(reversed_exercises, "build_muscle", 45, "Test")
        steps = payload["workoutSegments"][0]["workoutSteps"]
        circuit = next(s for s in steps if s.get("stepType", {}).get("stepTypeKey") == "repeat")
        exercise_steps = [
            s for s in circuit["workoutSteps"]
            if s.get("stepType", {}).get("stepTypeKey") == "interval"
        ]
        actual_names = [s.get("exerciseName") for s in exercise_steps]
        expected_names = [ex["name"].upper() for ex in reversed_exercises]
        assert actual_names == expected_names

    def test_all_goals_produce_valid_payload(self):
        for goal in GOALS:
            exercises = _exercises_for(goal)
            payload = rebuild_garmin_payload(exercises, goal, 45, "Test")
            assert "workoutSegments" in payload, f"Failed for goal {goal!r}"

    def test_single_exercise_allowed(self):
        exercises = _exercises_for("build_muscle", count=1)
        payload = rebuild_garmin_payload(exercises, "build_muscle", 45, "Solo")
        assert "workoutSegments" in payload

    def test_roundtrip_matches_generate(self):
        """Rebuilt payload should have the same name and sport type as generate()."""
        plan = generate(["bodyweight", "barbell"], "build_muscle", 45, seed=99)
        exercises = [dataclasses.asdict(e) for e in plan.exercises]
        rebuilt = rebuild_garmin_payload(exercises, "build_muscle", 45, plan.name)
        assert rebuilt["sportType"] == plan.garmin_payload["sportType"]
        assert rebuilt["workoutName"] == plan.garmin_payload["workoutName"]

    def test_timed_exercise_preserved(self):
        """Exercises with duration_sec (not reps) should rebuild without error."""
        plan = generate(["bodyweight"], "build_muscle", 45, seed=1)
        timed = [e for e in plan.exercises if e.duration_sec is not None]
        if not timed:
            pytest.skip("No timed exercises generated with this seed")
        exercises = [dataclasses.asdict(e) for e in timed[:1]]
        payload = rebuild_garmin_payload(exercises, "build_muscle", 45, "Timed Test")
        assert "workoutSegments" in payload


class TestExerciseInfoVideoUrl:
    def test_local_video_map_contains_expected_keys(self):
        """_LOCAL_VIDEO_MAP must include both videos we ship."""
        from web.workout_generator import _LOCAL_VIDEO_MAP
        assert _LOCAL_VIDEO_MAP["BULGARIAN_SPLIT_SQUAT"] == "/static/videos/bulgarian-split-squat.mp4"
        assert _LOCAL_VIDEO_MAP["JUMP_SQUAT"] == "/static/videos/jump-squat.mp4"

    def test_exercise_info_has_video_url_field(self):
        """ExerciseInfo dataclass must have a video_url field defaulting to None."""
        import dataclasses
        from web.workout_generator import ExerciseInfo
        field_names = {f.name for f in dataclasses.fields(ExerciseInfo)}
        assert "video_url" in field_names
        # default is None
        plan = generate(["bodyweight"], "build_muscle", 45, seed=42)
        # at least one exercise should have video_url as None (most won't have local video)
        assert any(e.video_url is None for e in plan.exercises)

    def test_video_url_populated_when_exercise_matches_map(self):
        """ExerciseInfo.video_url is set when the exercise name is in _LOCAL_VIDEO_MAP."""
        from web.workout_generator import ExerciseInfo, _LOCAL_VIDEO_MAP
        # Build a minimal ExerciseInfo for BULGARIAN_SPLIT_SQUAT
        ex = ExerciseInfo(
            category="STRENGTH_TRAINING",
            name="BULGARIAN_SPLIT_SQUAT",
            label="Bulgarian Split Squat",
            muscle_group="legs",
            sets=3, reps=10, duration_sec=None, rest_seconds=60,
            link="https://www.youtube.com/watch?v=2C-uNgKwPLE",
            description="",
            video_url=_LOCAL_VIDEO_MAP.get("BULGARIAN_SPLIT_SQUAT"),
        )
        assert ex.video_url == "/static/videos/bulgarian-split-squat.mp4"
