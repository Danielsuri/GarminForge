"""Unit tests for scripts/exercisedb_map.garmin_to_exercisedb_name()."""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))
from exercisedb_map import garmin_to_exercisedb_name, MANUAL_OVERRIDES


class TestAutoConversion:
    def test_barbell_bench_press(self) -> None:
        assert garmin_to_exercisedb_name("BARBELL_BENCH_PRESS") == "barbell bench press"

    def test_dumbbell_curl(self) -> None:
        assert garmin_to_exercisedb_name("DUMBBELL_CURL") == "dumbbell curl"

    def test_pull_up(self) -> None:
        assert garmin_to_exercisedb_name("PULL_UP") == "pull up"

    def test_plank(self) -> None:
        assert garmin_to_exercisedb_name("PLANK") == "plank"

    def test_burpee(self) -> None:
        assert garmin_to_exercisedb_name("BURPEE") == "burpee"

    def test_unknown_key_auto_converts(self) -> None:
        assert garmin_to_exercisedb_name("SOME_NEW_EXERCISE") == "some new exercise"


class TestManualOverrides:
    def test_barbell_back_squat_override(self) -> None:
        assert garmin_to_exercisedb_name("BARBELL_BACK_SQUAT") == "barbell squat"

    def test_dumbbell_lateral_raise_override(self) -> None:
        assert garmin_to_exercisedb_name("DUMBBELL_LATERAL_RAISE") == "lateral raise"

    def test_push_returns_none(self) -> None:
        assert garmin_to_exercisedb_name("PUSH") is None

    def test_forward_drag_returns_none(self) -> None:
        assert garmin_to_exercisedb_name("FORWARD_DRAG") is None

    def test_row_returns_none(self) -> None:
        assert garmin_to_exercisedb_name("ROW") is None

    def test_clean_and_press_returns_none(self) -> None:
        assert garmin_to_exercisedb_name("CLEAN_AND_PRESS") is None

    def test_shouldering_returns_none(self) -> None:
        assert garmin_to_exercisedb_name("SHOULDERING") is None


class TestReturnTypes:
    def test_returns_str_for_auto(self) -> None:
        assert isinstance(garmin_to_exercisedb_name("BARBELL_BENCH_PRESS"), str)

    def test_returns_str_for_string_override(self) -> None:
        assert isinstance(garmin_to_exercisedb_name("BARBELL_BACK_SQUAT"), str)

    def test_returns_none_for_none_override(self) -> None:
        assert garmin_to_exercisedb_name("PUSH") is None

    def test_never_raises(self) -> None:
        for key in ["", "X", "SOME_KEY_NOT_IN_MAP"]:
            try:
                garmin_to_exercisedb_name(key)
            except Exception as exc:
                pytest.fail(f"Raised {exc!r} for key {key!r}")
