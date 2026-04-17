"""add preferred_lang to users

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-03
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("preferred_lang", sa.String(5), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "preferred_lang")
