"""
Database engine, session factory, and Base for GarminForge.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DB_PATH = Path(os.environ.get("GARMINFORGE_DB_PATH", str(Path.home() / ".garminforge.db")))
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Create all tables if they don't exist. Called at startup via lifespan.

    Also applies additive column migrations (ALTER TABLE ADD COLUMN) that
    ``create_all`` skips on existing databases.  SQLite silently errors when a
    column already exists, so we swallow those exceptions.
    """
    from web.models import Program, ProgramSession, SavedPlan, User, WorkoutSession  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Add columns introduced after the initial schema.
    # Each statement is idempotent: the except swallows "duplicate column" errors.
    _additive_migrations = [
        "ALTER TABLE users ADD COLUMN preferred_lang VARCHAR(5)",
        "ALTER TABLE users ADD COLUMN questionnaire_completed BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE users ADD COLUMN age INTEGER",
        "ALTER TABLE users ADD COLUMN diet_json TEXT",
        "ALTER TABLE users ADD COLUMN health_conditions_json TEXT",
        "ALTER TABLE users ADD COLUMN preferred_equipment_json TEXT",
        "ALTER TABLE users ADD COLUMN fitness_level VARCHAR(20)",
        "ALTER TABLE users ADD COLUMN fitness_goals_json TEXT",
        "ALTER TABLE users ADD COLUMN weekly_workout_days INTEGER",
        "ALTER TABLE saved_plans ADD COLUMN program_session_id VARCHAR(36)",
    ]
    with engine.begin() as conn:
        for stmt in _additive_migrations:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass  # column already exists
