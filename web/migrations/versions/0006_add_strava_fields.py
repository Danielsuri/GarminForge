"""add strava fields to users and program_sessions

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-17
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("strava_athlete_id", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("strava_token_json", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("strava_activities_json", sa.Text(), nullable=True))
    op.add_column(
        "users",
        sa.Column("strava_synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "program_sessions",
        sa.Column("actual_duration_minutes", sa.Integer(), nullable=True),
    )
    op.add_column(
        "program_sessions",
        sa.Column("strava_activity_id", sa.String(32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("program_sessions", "strava_activity_id")
    op.drop_column("program_sessions", "actual_duration_minutes")
    op.drop_column("users", "strava_synced_at")
    op.drop_column("users", "strava_activities_json")
    op.drop_column("users", "strava_token_json")
    op.drop_column("users", "strava_athlete_id")
