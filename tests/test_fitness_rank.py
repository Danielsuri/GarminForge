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
    assert rf.rank_after == 3.5
    assert rf.trigger == "post_workout"
