"""add age_range, preferred_days_json, height_cm, weight_kg to users

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-11
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("age_range", sa.String(10), nullable=True))
    op.add_column("users", sa.Column("preferred_days_json", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("height_cm", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("weight_kg", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "weight_kg")
    op.drop_column("users", "height_cm")
    op.drop_column("users", "preferred_days_json")
    op.drop_column("users", "age_range")
