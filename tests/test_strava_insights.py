"""Tests for web.strava_insights."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock


from web.strava_insights import (
    RecoveryStatus,
    calibrate_fitness_rank,
    compact_activity,
    recovery_score,
    reschedule_if_needed,
)


def _activity(
    sport_type: str = "Run",
    elapsed_time: int = 3600,
    distance: float = 10000,
    average_heartrate: float = 150,
    max_heartrate: float = 170,
    suffer_score: int = 50,
    hours_ago: float = 24,
) -> dict:
    start = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return {
        "id": 1,
        "name": "Test Activity",
        "sport_type": sport_type,
        "start_date": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "elapsed_time": elapsed_time,
        "distance": distance,
        "average_heartrate": average_heartrate,
        "max_heartrate": max_heartrate,
        "suffer_score": suffer_score,
    }


# compact_activity

def test_compact_strips_extra_fields() -> None:
    raw = _activity()
    raw["extra_field"] = "should_be_removed"
    raw["another_extra"] = 999
    result = compact_activity(raw)
    assert "extra_field" not in result
    assert "another_extra" not in result
    assert "sport_type" in result
    assert "elapsed_time" in result


def test_compact_preserves_all_required_fields() -> None:
    raw = _activity()
    result = compact_activity(raw)
    for field in ("id", "name", "sport_type", "start_date", "elapsed_time",
                  "distance", "average_heartrate", "max_heartrate", "suffer_score"):
        assert field in result


def test_compact_handles_missing_optional_fields() -> None:
    raw = {"id": 1, "name": "Minimal", "sport_type": "Run",
           "start_date": "2026-01-01T10:00:00Z", "elapsed_time": 1800}
    result = compact_activity(raw)
    assert result["id"] == 1
    assert result.get("average_heartrate") is None


# calibrate_fitness_rank

def test_calibrate_returns_current_rank_when_no_activities() -> None:
    result = calibrate_fitness_rank([], current_rank=5.0)
    assert result == 5.0


def test_calibrate_blends_with_existing_rank() -> None:
    activities = [_activity(hours_ago=i * 24) for i in range(10)]
    result = calibrate_fitness_rank(activities, current_rank=5.0)
    assert 1.0 <= result <= 10.0


def test_calibrate_clamps_to_valid_range() -> None:
    activities = [_activity(suffer_score=200, elapsed_time=7200, hours_ago=i * 12)
                  for i in range(30)]
    result = calibrate_fitness_rank(activities, current_rank=10.0)
    assert result <= 10.0

    result_low = calibrate_fitness_rank([], current_rank=1.0)
    assert result_low >= 1.0


def test_calibrate_returns_1_when_no_activities_and_no_rank() -> None:
    result = calibrate_fitness_rank([], current_rank=None)
    assert result == 1.0


# recovery_score

def test_recovery_fully_fresh_when_no_recent_activity() -> None:
    activities = [_activity(hours_ago=72), _activity(hours_ago=96)]
    status = recovery_score(activities)
    assert status.recommended_rest_days == 0
    assert not status.fatigued
    assert status.score >= 0.8


def test_recovery_hard_effort_requires_two_days() -> None:
    activities = [_activity(suffer_score=90, hours_ago=12)]
    status = recovery_score(activities)
    assert status.recommended_rest_days == 2
    assert status.fatigued


def test_recovery_moderate_effort_requires_one_day() -> None:
    activities = [_activity(suffer_score=55, hours_ago=18)]
    status = recovery_score(activities)
    assert status.recommended_rest_days == 1


def test_recovery_next_safe_date_is_today_when_rested() -> None:
    activities = [_activity(hours_ago=72)]
    status = recovery_score(activities)
    assert status.next_safe_date == date.today()


def test_recovery_next_safe_date_offset_by_rest_days() -> None:
    activities = [_activity(suffer_score=90, hours_ago=12)]
    status = recovery_score(activities)
    expected = date.today() + timedelta(days=2)
    assert status.next_safe_date == expected


def test_recovery_summary_is_non_empty_string() -> None:
    status = recovery_score([])
    assert isinstance(status.summary, str)
    assert len(status.summary) > 0


# reschedule_if_needed

def _make_session(scheduled_date: date) -> MagicMock:
    s = MagicMock()
    s.scheduled_date = scheduled_date
    return s


def test_reschedule_does_nothing_when_rested() -> None:
    tomorrow = date.today() + timedelta(days=1)
    session = _make_session(tomorrow)
    recovery = RecoveryStatus(
        score=0.9, fatigued=False, recommended_rest_days=0,
        next_safe_date=date.today(), summary="Fresh"
    )
    db = MagicMock()
    reschedule_if_needed([session], recovery, db)
    assert session.scheduled_date == tomorrow


def test_reschedule_delays_sessions_in_recovery_window() -> None:
    tomorrow = date.today() + timedelta(days=1)
    next_safe = date.today() + timedelta(days=2)
    session = _make_session(tomorrow)
    recovery = RecoveryStatus(
        score=0.2, fatigued=True, recommended_rest_days=2,
        next_safe_date=next_safe, summary="Exhausted"
    )
    db = MagicMock()
    reschedule_if_needed([session], recovery, db)
    assert session.scheduled_date == next_safe + timedelta(days=1)
    db.commit.assert_called_once()


def test_reschedule_does_not_pull_sessions_earlier() -> None:
    far_future = date.today() + timedelta(days=10)
    session = _make_session(far_future)
    next_safe = date.today() + timedelta(days=2)
    recovery = RecoveryStatus(
        score=0.2, fatigued=True, recommended_rest_days=2,
        next_safe_date=next_safe, summary="Exhausted"
    )
    db = MagicMock()
    reschedule_if_needed([session], recovery, db)
    assert session.scheduled_date == far_future
