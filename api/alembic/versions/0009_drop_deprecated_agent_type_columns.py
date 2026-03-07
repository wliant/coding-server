"""drop deprecated dev_agent_type and test_agent_type columns

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("jobs", "dev_agent_type")
    op.drop_column("jobs", "test_agent_type")


def downgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column(
            "test_agent_type",
            sa.String(50),
            nullable=True,
        ),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "dev_agent_type",
            sa.String(50),
            nullable=True,
        ),
    )
