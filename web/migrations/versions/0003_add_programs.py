"""add Program and ProgramSession tables; program_session_id on saved_plans

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-07
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "programs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("goal", sa.String(50), nullable=False),
        sa.Column("periodization_type", sa.String(20), nullable=False),
        sa.Column("duration_weeks", sa.Integer, nullable=False),
        sa.Column("equipment_json", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_programs_user_id", "programs", ["user_id"])

    op.create_table(
        "program_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "program_id",
            sa.String(36),
            sa.ForeignKey("programs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("week_num", sa.Integer, nullable=False),
        sa.Column("day_num", sa.Integer, nullable=False),
        sa.Column("focus", sa.String(100), nullable=False),
        sa.Column("garmin_payload_json", sa.Text, nullable=False),
        sa.Column("exercises_json", sa.Text, nullable=False),
        sa.Column("garmin_workout_id", sa.String(100), nullable=True),
        sa.Column("scheduled_date", sa.Date, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_program_sessions_program_id", "program_sessions", ["program_id"])

    # SQLite does not support adding FK constraints via ALTER TABLE ADD COLUMN.
    # The FK relationship is declared in the ORM model and enforced at the application layer.
    # A future migration to PostgreSQL would require op.create_foreign_key() here.
    op.add_column("saved_plans", sa.Column("program_session_id", sa.String(36), nullable=True))


def downgrade() -> None:
    op.drop_column("saved_plans", "program_session_id")
    op.drop_index("ix_program_sessions_program_id", table_name="program_sessions")
    op.drop_table("program_sessions")
    op.drop_index("ix_programs_user_id", table_name="programs")
    op.drop_table("programs")
