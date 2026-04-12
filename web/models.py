"""
SQLAlchemy ORM models for GarminForge user management and progress tracking.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from web.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(128), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    google_sub: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True, index=True)
    apple_sub: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    garmin_token_b64: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_lang: Mapped[str | None] = mapped_column(String(5), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Onboarding questionnaire
    questionnaire_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    age_range: Mapped[str | None] = mapped_column(String(10), nullable=True)      # "18-29" | "30-39" | "40-49" | "50+"
    preferred_days_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list e.g. '["Mon","Wed","Fri"]'
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    diet_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    health_conditions_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_equipment_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    fitness_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fitness_goals_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    weekly_workout_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fitness_rank: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 1.0–10.0, null until questionnaire is completed. Updated via /my/rank-feedback.

    plans: Mapped[list[SavedPlan]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[list[WorkoutSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    programs: Mapped[list[Program]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class SavedPlan(Base):
    __tablename__ = "saved_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    goal: Mapped[str] = mapped_column(String(50), nullable=False)
    equipment_json: Mapped[str] = mapped_column(Text, nullable=False)
    duration_minutes: Mapped[int]
    exercises_json: Mapped[str] = mapped_column(Text, nullable=False)
    garmin_payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    program_session_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("program_sessions.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="plans")
    sessions: Mapped[list[WorkoutSession]] = relationship(back_populates="plan")
    program_session: Mapped[ProgramSession | None] = relationship(back_populates="saved_plans")


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("saved_plans.id", ondelete="SET NULL"), nullable=True
    )
    plan_name: Mapped[str] = mapped_column(String(200), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    exercises_completed: Mapped[int] = mapped_column(default=0)
    total_exercises: Mapped[int] = mapped_column(default=0)
    rounds_completed: Mapped[int] = mapped_column(default=0)
    total_rounds: Mapped[int] = mapped_column(default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions")
    plan: Mapped[SavedPlan | None] = relationship(back_populates="sessions")


class RankFeedback(Base):
    __tablename__ = "rank_feedbacks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("workout_sessions.id", ondelete="SET NULL"), nullable=True
    )
    trigger: Mapped[str] = mapped_column(String(20), nullable=False)
    # "mid_workout" | "post_workout"
    feedback: Mapped[str] = mapped_column(String(20), nullable=False)
    # "too_easy" | "just_right" | "too_hard"
    delta: Mapped[float] = mapped_column(Float, nullable=False)
    rank_before: Mapped[float] = mapped_column(Float, nullable=False)
    rank_after: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    goal: Mapped[str] = mapped_column(String(50), nullable=False)
    periodization_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # "linear" | "undulating" | "block"
    duration_weeks: Mapped[int] = mapped_column(Integer, nullable=False)
    equipment_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    # "active" | "completed" | "paused"
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="programs")
    program_sessions: Mapped[list[ProgramSession]] = relationship(
        back_populates="program", cascade="all, delete-orphan"
    )


class ProgramSession(Base):
    __tablename__ = "program_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    program_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    week_num: Mapped[int] = mapped_column(Integer, nullable=False)
    day_num: Mapped[int] = mapped_column(Integer, nullable=False)
    focus: Mapped[str] = mapped_column(String(100), nullable=False)
    garmin_payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    exercises_json: Mapped[str] = mapped_column(Text, nullable=False)
    garmin_workout_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    program: Mapped[Program] = relationship(back_populates="program_sessions")
    saved_plans: Mapped[list[SavedPlan]] = relationship(back_populates="program_session")
