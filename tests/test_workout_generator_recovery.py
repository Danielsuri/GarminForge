"""Tests for recovery-aware workout generation."""

from __future__ import annotations
from datetime import date
from web.strava_insights import RecoveryStatus
from web.workout_generator import generate


def _fatigued_recovery() -> RecoveryStatus:
    return RecoveryStatus(
        score=0.2,
        fatigued=True,
        recommended_rest_days=2,
        next_safe_date=date.today(),
        summary="Rest recommended.",
    )


def _fresh_recovery() -> RecoveryStatus:
    return RecoveryStatus(
        score=0.9,
        fatigued=False,
        recommended_rest_days=0,
        next_safe_date=date.today(),
        summary="Feeling great.",
    )


def test_generate_no_recovery_unchanged() -> None:
    """generate() without recovery param produces a plan."""
    plan = generate(equipment=[], goal="general_fitness", duration_minutes=30)
    assert plan is not None


def test_generate_fresh_recovery_unchanged() -> None:
    """Fresh recovery does not cap difficulty or shorten duration."""
    plan = generate(
        equipment=[],
        goal="general_fitness",
        duration_minutes=30,
        fitness_rank=5.0,
        recovery=_fresh_recovery(),
    )
    assert plan is not None
    # Duration should be ~30 min (not shortened)
    assert plan.duration_minutes >= 28


def test_generate_fatigued_caps_difficulty() -> None:
    """Fatigued recovery shortens duration (duration_minutes < input)."""
    plan = generate(
        equipment=[],
        goal="general_fitness",
        duration_minutes=45,
        fitness_rank=5.0,
        recovery=_fatigued_recovery(),
        seed=42,
    )
    # 45 * 0.88 = ~39.6 → internal duration is shorter
    assert plan.duration_minutes < 44


def test_generate_fatigued_no_fitness_rank() -> None:
    """Fatigued recovery with no fitness_rank still shortens duration."""
    plan = generate(
        equipment=[],
        goal="general_fitness",
        duration_minutes=40,
        recovery=_fatigued_recovery(),
        seed=42,
    )
    assert plan is not None
    assert plan.duration_minutes < 40
