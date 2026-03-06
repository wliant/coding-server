"""add job lease fields

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-06 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("lease_holder", sa.String(36), nullable=True))
    op.add_column("jobs", sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "lease_expires_at")
    op.drop_column("jobs", "lease_holder")
