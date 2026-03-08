"""add assigned_worker_id and assigned_worker_url to jobs

Revision ID: 0010
Revises: 0009
Create Date: 2026-03-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("assigned_worker_id", sa.String(255), nullable=True))
    op.add_column("jobs", sa.Column("assigned_worker_url", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "assigned_worker_url")
    op.drop_column("jobs", "assigned_worker_id")
