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


def test_health_exclusion_live_names_exist_in_pool():
    """ALTERNATING_SQUAT_WAVE is in both heart_condition and asthma exclusions,
    and it actually exists in _POOL."""
    pool_names = {ex.name for ex in _POOL}
    assert "ALTERNATING_SQUAT_WAVE" in _HEALTH_EXCLUSIONS["heart_condition"]
    assert "ALTERNATING_SQUAT_WAVE" in _HEALTH_EXCLUSIONS["asthma"]
    assert "ALTERNATING_SQUAT_WAVE" in pool_names


def test_rank_band_widens_when_pool_too_small():
    """With bodyweight-only equipment and rank=10.0, the ±2 band has < num exercises,
    so the selector must widen to ±3 or beyond. At least one returned exercise must
    have difficulty < 8 (proving the band widened past the ±2 threshold)."""
    plan = generate(
        equipment=["bodyweight"],
        goal="build_muscle",
        duration_minutes=30,
        fitness_rank=10.0,
        seed=42,
    )
    assert len(plan.exercises) > 0
    pool_by_name = {ex.name: ex for ex in _POOL}
    # At rank=10 with band=2 only difficulty>=8 is in-band.
    # If any returned exercise has difficulty<8, the widening path fired.
    difficulties = [pool_by_name[ex.name].difficulty for ex in plan.exercises if ex.name in pool_by_name]
    assert any(d < 8 for d in difficulties), (
        f"Expected at least one difficulty<8 exercise (band-widening proof), got difficulties={difficulties}"
    )


def test_generate_with_heart_condition_excludes_alternating_squat_wave():
    """Users with heart_condition must never receive ALTERNATING_SQUAT_WAVE or ALTERNATING_WAVE.
    Uses battle_rope + bodyweight equipment so the pool is non-empty after exclusions."""
    plan = generate(
        equipment=["battle_rope", "bodyweight"],
        goal="build_muscle",
        duration_minutes=45,
        health_conditions=["heart_condition"],
        seed=42,
    )
    assert len(plan.exercises) > 0, "Expected non-empty plan (bodyweight exercises should fill the pool)"
    names = {ex.name for ex in plan.exercises}
    assert "ALTERNATING_WAVE" not in names
    assert "ALTERNATING_SQUAT_WAVE" not in names


# ---------------------------------------------------------------------------
# Task 6: PATCH /my/rank-feedback endpoint
# ---------------------------------------------------------------------------
from fastapi.testclient import TestClient
from web.app import app
from web.db import get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _make_test_client(fitness_rank: float):
    """Create a TestClient with an in-memory DB and a mocked authenticated user."""
    from sqlalchemy import StaticPool
    from web.db import Base as _Base

    # Use StaticPool so all connections share the same in-memory DB instance
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    db = SessionLocal()
    from web.models import User as _User
    user = _User(email="t@t.com", hashed_password="x", fitness_rank=fitness_rank,
                 questionnaire_completed=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    user_id = user.id
    db.close()

    import web.routes_my as _routes_my

    _original = _routes_my._require_user

    # Monkeypatch _require_user in routes_my to look up user in the test DB.
    # We use the db session provided by the endpoint (which comes from our
    # override_get_db), so that mutations to user.fitness_rank are committed
    # to the same in-memory engine we later query for assertions.
    def _fake_require_user(request, db):
        return db.get(_User, user_id)

    _routes_my._require_user = _fake_require_user  # type: ignore[assignment]

    client = TestClient(app, raise_server_exceptions=True)

    return client, user_id, SessionLocal, _routes_my, _original


def test_rank_feedback_too_easy_post_increases_rank():
    client, user_id, SL, routes_my, orig = _make_test_client(3.0)
    try:
        resp = client.patch("/my/rank-feedback", json={"trigger": "post_workout", "feedback": "too_easy"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["rank_before"] == 3.0
        assert data["rank_after"] == 3.5
        db = SL()
        from web.models import User as _U
        u = db.get(_U, user_id)
        assert u.fitness_rank == 3.5
        db.close()
    finally:
        routes_my._require_user = orig
        app.dependency_overrides.pop(get_db, None)


def test_rank_feedback_too_hard_post_decreases_rank():
    client, _, _, routes_my, orig = _make_test_client(5.0)
    try:
        resp = client.patch("/my/rank-feedback", json={"trigger": "post_workout", "feedback": "too_hard"})
        assert resp.status_code == 200
        assert resp.json()["rank_after"] == 4.5
    finally:
        routes_my._require_user = orig
        app.dependency_overrides.pop(get_db, None)


def test_rank_feedback_just_right_no_change():
    client, _, _, routes_my, orig = _make_test_client(5.0)
    try:
        resp = client.patch("/my/rank-feedback", json={"trigger": "post_workout", "feedback": "just_right"})
        assert resp.status_code == 200
        assert resp.json()["rank_after"] == 5.0
    finally:
        routes_my._require_user = orig
        app.dependency_overrides.pop(get_db, None)


def test_rank_feedback_mid_workout_too_easy():
    client, _, _, routes_my, orig = _make_test_client(5.0)
    try:
        resp = client.patch("/my/rank-feedback", json={"trigger": "mid_workout", "feedback": "too_easy"})
        assert resp.status_code == 200
        import pytest as _pytest
        assert resp.json()["rank_after"] == _pytest.approx(5.1)
    finally:
        routes_my._require_user = orig
        app.dependency_overrides.pop(get_db, None)


def test_rank_feedback_clamped_at_max():
    client, _, _, routes_my, orig = _make_test_client(9.8)
    try:
        resp = client.patch("/my/rank-feedback", json={"trigger": "post_workout", "feedback": "too_easy"})
        assert resp.status_code == 200
        assert resp.json()["rank_after"] == 10.0
    finally:
        routes_my._require_user = orig
        app.dependency_overrides.pop(get_db, None)


def test_rank_feedback_clamped_at_min():
    client, _, _, routes_my, orig = _make_test_client(1.2)
    try:
        resp = client.patch("/my/rank-feedback", json={"trigger": "post_workout", "feedback": "too_hard"})
        assert resp.status_code == 200
        assert resp.json()["rank_after"] == 1.0
    finally:
        routes_my._require_user = orig
        app.dependency_overrides.pop(get_db, None)


def test_rank_feedback_mid_just_right_invalid():
    client, _, _, routes_my, orig = _make_test_client(5.0)
    try:
        resp = client.patch("/my/rank-feedback", json={"trigger": "mid_workout", "feedback": "just_right"})
        assert resp.status_code == 400
    finally:
        routes_my._require_user = orig
        app.dependency_overrides.pop(get_db, None)
