"""add agent_id to jobs

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-06 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_jobs_agent_id",
        "jobs",
        "agents",
        ["agent_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_jobs_agent_id", "jobs", type_="foreignkey")
    op.drop_column("jobs", "agent_id")
