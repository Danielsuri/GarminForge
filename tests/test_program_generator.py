"""Tests for web/program_generator.py."""
from __future__ import annotations

import pytest

from web.program_generator import (
    _phase_params,
    generate_program,
)


# ---------------------------------------------------------------------------
# _phase_params — linear
# ---------------------------------------------------------------------------

class TestLinearPhaseParams:
    def test_8week_accumulation(self) -> None:
        p = _phase_params(1, 8, "linear", 0)
        assert p.sets == 3
        assert p.reps_high == 15
        assert p.rest_seconds == 60

    def test_8week_deload_week4(self) -> None:
        p = _phase_params(4, 8, "linear", 0)
        assert p.sets == 2

    def test_8week_intensification_week5(self) -> None:
        p = _phase_params(5, 8, "linear", 0)
        assert p.sets == 4
        assert p.reps_high == 10
        assert p.rest_seconds == 90

    def test_8week_peak_week8(self) -> None:
        p = _phase_params(8, 8, "linear", 0)
        assert p.sets == 5
        assert p.reps_high == 5
        assert p.rest_seconds == 120

    def test_4week_no_deload(self) -> None:
        # Week 3 should be intensification (not deload) for 4-week programs
        p = _phase_params(3, 4, "linear", 0)
        assert p.sets == 4

    def test_6week_deload_week3(self) -> None:
        p = _phase_params(3, 6, "linear", 0)
        assert p.sets == 2


# ---------------------------------------------------------------------------
# _phase_params — undulating
# ---------------------------------------------------------------------------

class TestUndulatingPhaseParams:
    def test_day0_is_strength(self) -> None:
        p = _phase_params(1, 8, "undulating", 0)
        assert p.sets == 5
        assert p.reps_high == 5

    def test_day1_is_hypertrophy(self) -> None:
        p = _phase_params(1, 8, "undulating", 1)
        assert p.sets == 4
        assert p.reps_high == 12

    def test_day2_is_endurance(self) -> None:
        p = _phase_params(1, 8, "undulating", 2)
        assert p.sets == 3
        assert p.reps_high == 15

    def test_day3_cycles_back_to_strength(self) -> None:
        p3 = _phase_params(1, 8, "undulating", 3)
        p0 = _phase_params(1, 8, "undulating", 0)
        assert p3 == p0

    def test_same_pattern_every_week(self) -> None:
        week1 = _phase_params(1, 8, "undulating", 0)
        week5 = _phase_params(5, 8, "undulating", 0)
        assert week1 == week5


# ---------------------------------------------------------------------------
# _phase_params — block
# ---------------------------------------------------------------------------

class TestBlockPhaseParams:
    def test_8week_accumulation(self) -> None:
        # block_size = 8//3 = 2; acc weeks = 1,2
        p = _phase_params(1, 8, "block", 0)
        assert p.sets == 3

    def test_8week_deload(self) -> None:
        # deload week = 3
        p = _phase_params(3, 8, "block", 0)
        assert p.sets == 2

    def test_8week_intensification(self) -> None:
        # int weeks = 4,5
        p = _phase_params(4, 8, "block", 0)
        assert p.sets == 4

    def test_8week_peak(self) -> None:
        # peak weeks = 6,7,8
        p = _phase_params(6, 8, "block", 0)
        assert p.sets == 5

    def test_4week_no_deload(self) -> None:
        # 4-week has no deload (n < 6)
        # block_size = 4//3 = 1; acc=week1, int=week2, peak=week3,4
        p = _phase_params(2, 4, "block", 0)
        assert p.sets == 4  # int


# ---------------------------------------------------------------------------
# generate_program
# ---------------------------------------------------------------------------

class TestGenerateProgram:
    def test_session_count(self) -> None:
        plan = generate_program(
            goal="build_muscle",
            equipment=["barbell", "dumbbell"],
            duration_weeks=4,
            weekly_workout_days=3,
            duration_minutes=45,
        )
        assert len(plan.sessions) == 4 * 3  # 12 sessions

    def test_session_count_8x5(self) -> None:
        plan = generate_program(
            goal="general_fitness",
            equipment=["bodyweight"],
            duration_weeks=8,
            weekly_workout_days=5,
            duration_minutes=30,
        )
        assert len(plan.sessions) == 8 * 5  # 40 sessions

    def test_week_day_numbering(self) -> None:
        plan = generate_program(
            goal="build_strength",
            equipment=["barbell"],
            duration_weeks=4,
            weekly_workout_days=3,
            duration_minutes=60,
        )
        week_days = [(s.week_num, s.day_num) for s in plan.sessions]
        expected = [(w, d) for w in range(1, 5) for d in range(1, 4)]
        assert week_days == expected

    def test_program_plan_fields(self) -> None:
        plan = generate_program(
            goal="burn_fat",
            equipment=["dumbbell"],
            duration_weeks=6,
            weekly_workout_days=2,
            duration_minutes=30,
            periodization_type="linear",
        )
        assert plan.goal == "burn_fat"
        assert plan.duration_weeks == 6
        assert plan.weekly_workout_days == 2
        assert plan.periodization_type == "linear"
        assert "6-Week" in plan.name

    def test_workout_name_format(self) -> None:
        plan = generate_program(
            goal="general_fitness",
            equipment=["bodyweight"],
            duration_weeks=4,
            weekly_workout_days=3,
            duration_minutes=45,
        )
        s = plan.sessions[0]
        assert "Week 1 Day 1" in s.workout_name
        assert "45 min" in s.workout_name

    def test_linear_phase_sets_progression(self) -> None:
        plan = generate_program(
            goal="build_muscle",
            equipment=["barbell", "dumbbell"],
            duration_weeks=8,
            weekly_workout_days=3,
            duration_minutes=60,
            periodization_type="linear",
        )
        # Week 1 = acc (3 sets), Week 5 = int (4 sets), Week 8 = peak (5 sets)
        week1_sets = plan.sessions[0].sets   # week 1, day 1
        week5_sets = plan.sessions[4 * 3].sets  # week 5, day 1
        week8_sets = plan.sessions[7 * 3].sets  # week 8, day 1
        assert week1_sets == 3
        assert week5_sets == 4
        assert week8_sets == 5

    def test_undulating_rotates_rep_ranges(self) -> None:
        plan = generate_program(
            goal="general_fitness",
            equipment=["bodyweight"],
            duration_weeks=4,
            weekly_workout_days=3,
            duration_minutes=45,
            periodization_type="undulating",
        )
        # Sessions 0,1,2 = week 1 days 1,2,3 → strength, hypertrophy, endurance
        assert plan.sessions[0].reps_high == 5
        assert plan.sessions[1].reps_high == 12
        assert plan.sessions[2].reps_high == 15

    def test_each_session_has_garmin_payload(self) -> None:
        plan = generate_program(
            goal="lose_weight",
            equipment=["dumbbell"],
            duration_weeks=4,
            weekly_workout_days=2,
            duration_minutes=30,
        )
        for s in plan.sessions:
            assert isinstance(s.garmin_payload, dict)
            assert "workoutName" in s.garmin_payload

    def test_each_session_has_exercises(self) -> None:
        plan = generate_program(
            goal="build_muscle",
            equipment=["barbell"],
            duration_weeks=4,
            weekly_workout_days=3,
            duration_minutes=45,
        )
        for s in plan.sessions:
            assert len(s.exercises) > 0

    def test_deterministic_with_seed(self) -> None:
        kwargs = dict(
            goal="general_fitness",
            equipment=["bodyweight"],
            duration_weeks=4,
            weekly_workout_days=3,
            duration_minutes=30,
            seed=42,
        )
        plan_a = generate_program(**kwargs)  # type: ignore[arg-type]
        plan_b = generate_program(**kwargs)  # type: ignore[arg-type]
        names_a = [s.exercises[0].name for s in plan_a.sessions]
        names_b = [s.exercises[0].name for s in plan_b.sessions]
        assert names_a == names_b

    def test_split_focus_labels_3days(self) -> None:
        plan = generate_program(
            goal="build_muscle",
            equipment=["barbell", "dumbbell"],
            duration_weeks=4,
            weekly_workout_days=3,
            duration_minutes=45,
        )
        # First week: Push, Pull, Legs
        focuses = [s.focus for s in plan.sessions[:3]]
        assert focuses == ["Upper Body — Push", "Upper Body — Pull", "Lower Body"]

    def test_invalid_goal_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown goal"):
            generate_program(
                goal="invalid_goal",
                equipment=["barbell"],
                duration_weeks=4,
                weekly_workout_days=3,
                duration_minutes=45,
            )

    def test_invalid_periodization_raises(self) -> None:
        with pytest.raises(ValueError, match="periodization_type"):
            generate_program(
                goal="build_muscle",
                equipment=["barbell"],
                duration_weeks=4,
                weekly_workout_days=3,
                duration_minutes=45,
                periodization_type="invalid",
            )

    def test_bodyweight_fallback(self) -> None:
        # Empty equipment list should fall back to bodyweight
        plan = generate_program(
            goal="general_fitness",
            equipment=[],
            duration_weeks=4,
            weekly_workout_days=2,
            duration_minutes=30,
        )
        assert len(plan.sessions) == 8
        for s in plan.sessions:
            assert len(s.exercises) > 0
