"""Tests for fitness rank data model and rank computation."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from web.db import Base
from web.models import User, RankFeedback


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_user_fitness_rank_defaults_to_none(db):
    u = User(email="a@b.com", hashed_password="x")
    db.add(u)
    db.commit()
    db.refresh(u)
    assert u.fitness_rank is None


def test_rank_feedback_stores_delta(db):
    u = User(email="a@b.com", hashed_password="x")
    db.add(u)
    db.commit()
    rf = RankFeedback(
        user_id=u.id,
        trigger="post_workout",
        feedback="too_easy",
        delta=0.5,
        rank_before=3.0,
        rank_after=3.5,
    )
    db.add(rf)
    db.commit()
    db.refresh(rf)
    assert rf.delta == 0.5
    assert rf.rank_before == 3.0
    assert rf.rank_after == 3.5
    assert rf.trigger == "post_workout"
    assert rf.feedback == "too_easy"


from web.routes_onboarding import compute_initial_rank


def test_beginner_gets_low_rank():
    assert compute_initial_rank("Beginner", "18-29", []) == 2.0


def test_intermediate_base():
    assert compute_initial_rank("Intermediate", "30-39", []) == 5.0


def test_advanced_base():
    assert compute_initial_rank("Advanced", "40-49", []) == 8.0


def test_50_plus_penalty():
    assert compute_initial_rank("Intermediate", "50+", []) == 4.0


def test_health_penalty():
    assert compute_initial_rank("Intermediate", "30-39", ["joint_problems"]) == 4.5


def test_50_plus_beginner_with_health():
    # 2.0 - 1.0 - 0.5 = 0.5, clamped to 1.0
    assert compute_initial_rank("Beginner", "50+", ["back_pain"]) == 1.0


def test_advanced_no_penalty():
    assert compute_initial_rank("Advanced", "18-29", []) == 8.0


def test_none_fitness_level_falls_back():
    assert compute_initial_rank(None, None, []) == 3.0


def test_rank_clamped_at_10():
    assert compute_initial_rank("Advanced", "18-29", []) <= 10.0


from web.workout_generator import _POOL


def test_all_pool_exercises_have_difficulty():
    for ex in _POOL:
        assert hasattr(ex, "difficulty"), f"{ex.name} missing difficulty"
        assert 1 <= ex.difficulty <= 10, f"{ex.name} difficulty {ex.difficulty} out of range"


from web.workout_generator import generate, _HEALTH_EXCLUSIONS


def test_health_exclusions_dict_exists():
    assert "joint_problems" in _HEALTH_EXCLUSIONS
    assert "back_pain" in _HEALTH_EXCLUSIONS
    assert "heart_condition" in _HEALTH_EXCLUSIONS


def test_joint_problems_excludes_box_jump():
    excluded = _HEALTH_EXCLUSIONS["joint_problems"]
    assert "BOX_JUMP" in excluded
    assert "JUMP_SQUAT" in excluded
    assert "BURPEE" in excluded


def test_back_pain_excludes_deadlift():
    excluded = _HEALTH_EXCLUSIONS["back_pain"]
    assert "BARBELL_DEADLIFT" in excluded
    assert "GOOD_MORNING" in excluded


def test_generate_with_joint_problems_has_no_box_jump():
    plan = generate(
        equipment=["bodyweight", "box"],
        goal="general_fitness",
        duration_minutes=45,
        health_conditions=["joint_problems"],
        seed=42,
    )
    names = [ex.name for ex in plan.exercises]
    assert "BOX_JUMP" not in names
    assert "JUMP_SQUAT" not in names


def test_generate_with_rank_band_stays_within_range():
    plan = generate(
        equipment=["bodyweight", "dumbbell", "barbell", "cable", "machine"],
        goal="general_fitness",
        duration_minutes=45,
        fitness_rank=3.0,
        seed=42,
    )
    # All exercises must be within rank ± 4 (widest fallback band)
    for ex in plan.exercises:
        pool_ex = next(p for p in _POOL if p.name == ex.name)
        assert abs(pool_ex.difficulty - 3.0) <= 4, (
            f"{ex.name} difficulty {pool_ex.difficulty} too far from rank 3.0"
        )


def test_generate_without_rank_uses_full_pool():
    plan = generate(
        equipment=["bodyweight"],
        goal="general_fitness",
        duration_minutes=45,
        seed=42,
    )
    assert len(plan.exercises) > 0


def test_generate_no_health_conditions_allows_box_jump():
    # Without conditions, high-impact exercises can appear
    found = False
    for seed in range(50):
        plan = generate(
            equipment=["bodyweight", "box"],
            goal="general_fitness",
            duration_minutes=45,
            seed=seed,
        )
        if any(ex.name == "BOX_JUMP" for ex in plan.exercises):
            found = True
            break
    assert found, "BOX_JUMP never appeared without health restrictions (check equipment filter)"
