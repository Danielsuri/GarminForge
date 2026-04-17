"""Strava activity analysis: fitness rank calibration and recovery scoring.

All functions are pure and stateless — they operate on compact activity dicts
(the shape stored in User.strava_activities_json) and return plain values or
dataclasses. Database writes are isolated to reschedule_if_needed().
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from web.models import ProgramSession

logger = logging.getLogger(__name__)

_COMPACT_FIELDS = frozenset(
    {
        "id",
        "name",
        "sport_type",
        "start_date",
        "elapsed_time",
        "distance",
        "average_heartrate",
        "max_heartrate",
        "suffer_score",
    }
)

_DEFAULT_MAX_HR = 185
_HARD_SUFFER = 80
_MODERATE_SUFFER = 40
_RECOVERY_WINDOW_HOURS = 48


def compact_activity(raw: dict[str, Any]) -> dict[str, Any]:
    """Strip a full Strava activity payload down to the 9 fields we store."""
    return {k: raw.get(k) for k in _COMPACT_FIELDS}


def calibrate_fitness_rank(
    activities: list[dict[str, Any]],
    current_rank: float | None,
) -> float:
    """Estimate fitness rank from last 30 days of Strava activity.

    Blend 70% derived score + 30% existing rank so manual feedback still
    counts. Returns a value clamped to [1.0, 10.0].
    """
    if not activities and current_rank is None:
        return 1.0
    if not activities:
        return current_rank  # type: ignore[return-value]

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    recent = [a for a in activities if _parse_date(a.get("start_date", "")) >= cutoff]

    if not recent:
        return current_rank if current_rank is not None else 1.0

    total_seconds = sum(a.get("elapsed_time") or 0 for a in recent)
    weeks = max(len(recent) / 7, 1)
    avg_weekly_seconds = total_seconds / weeks
    volume_score = min(avg_weekly_seconds / (5 * 3600) * 5, 10.0)

    active_days = len({a.get("start_date", "")[:10] for a in recent})
    consistency_score = min(active_days / 30 * 10, 10.0)

    suffer_scores = [a.get("suffer_score") or 0 for a in recent]
    avg_suffer = sum(suffer_scores) / len(suffer_scores)
    intensity_score = min(avg_suffer / 100 * 10, 10.0)

    derived = volume_score * 0.5 + consistency_score * 0.3 + intensity_score * 0.2
    derived = max(1.0, min(derived, 10.0))

    if current_rank is None:
        return round(derived, 1)

    blended = 0.7 * derived + 0.3 * current_rank
    return round(max(1.0, min(blended, 10.0)), 1)


@dataclass
class RecoveryStatus:
    """Encapsulates current recovery state derived from recent Strava activity."""

    score: float
    fatigued: bool
    recommended_rest_days: int
    next_safe_date: date
    summary: str


def recovery_score(activities: list[dict[str, Any]]) -> RecoveryStatus:
    """Derive recovery status from activities in the past 48 hours."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=_RECOVERY_WINDOW_HOURS)
    recent = [a for a in activities if _parse_date(a.get("start_date", "")) >= cutoff]

    if not recent:
        return RecoveryStatus(
            score=1.0,
            fatigued=False,
            recommended_rest_days=0,
            next_safe_date=date.today(),
            summary="No recent activity — fully recovered.",
        )

    max_suffer = max((a.get("suffer_score") or 0 for a in recent), default=0)
    max_avg_hr = max((a.get("average_heartrate") or 0 for a in recent), default=0)
    hr_threshold_hard = _DEFAULT_MAX_HR * 0.85
    hr_threshold_moderate = _DEFAULT_MAX_HR * 0.70

    most_recent = sorted(recent, key=lambda a: a.get("start_date", ""), reverse=True)[0]
    sport = most_recent.get("sport_type", "activity")
    hours_since = (
        datetime.now(timezone.utc) - _parse_date(most_recent.get("start_date", ""))
    ).total_seconds() / 3600

    if max_suffer > _HARD_SUFFER or max_avg_hr > hr_threshold_hard:
        rest_days = 2
        score = 0.2
        summary = (
            f"Hard {sport.lower()} {hours_since:.0f}h ago "
            f"(suffer score {max_suffer}) — 2 rest days recommended."
        )
    elif max_suffer > _MODERATE_SUFFER or max_avg_hr > hr_threshold_moderate:
        rest_days = 1
        score = 0.5
        summary = (
            f"Moderate {sport.lower()} {hours_since:.0f}h ago "
            f"(suffer score {max_suffer}) — 1 rest day recommended."
        )
    else:
        rest_days = 0
        score = 0.8
        summary = f"Light {sport.lower()} {hours_since:.0f}h ago — ready to train."

    return RecoveryStatus(
        score=score,
        fatigued=score < 0.4,
        recommended_rest_days=rest_days,
        next_safe_date=date.today() + timedelta(days=rest_days),
        summary=summary,
    )


def reschedule_if_needed(
    sessions: "list[ProgramSession]",
    recovery: RecoveryStatus,
    db: "Session",
) -> "list[ProgramSession]":
    """Push ProgramSessions forward if their date falls in the recovery window.

    Delay only — never pull sessions earlier. Returns list of modified sessions.
    """
    if recovery.recommended_rest_days == 0:
        return []

    modified: list[Any] = []
    new_date = recovery.next_safe_date + timedelta(days=1)

    for session in sessions:
        if session.scheduled_date is None:
            continue
        if session.scheduled_date <= recovery.next_safe_date:
            logger.info(
                "Rescheduling session %s from %s to %s (recovery)",
                session.id,
                session.scheduled_date,
                new_date,
            )
            session.scheduled_date = new_date
            modified.append(session)

    if modified:
        db.commit()

    return modified


def _parse_date(date_str: str) -> datetime:
    """Parse a Strava ISO 8601 date string to a timezone-aware datetime."""
    if not date_str:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
