"""add fitness_rank to users and rank_feedbacks table

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-12
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("fitness_rank", sa.Float(), nullable=True))
    op.create_table(
        "rank_feedbacks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("workout_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("trigger", sa.String(20), nullable=False),
        sa.Column("feedback", sa.String(20), nullable=False),
        sa.Column("delta", sa.Float(), nullable=False),
        sa.Column("rank_before", sa.Float(), nullable=False),
        sa.Column("rank_after", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("rank_feedbacks")
    op.drop_column("users", "fitness_rank")
