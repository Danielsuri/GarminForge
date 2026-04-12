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
