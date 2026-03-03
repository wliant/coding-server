"""add task fields and settings

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-02 00:01:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add dev_agent_type column to jobs
    op.add_column(
        "jobs",
        sa.Column(
            "dev_agent_type",
            sa.String(50),
            nullable=False,
            server_default="spec_driven_development",
        ),
    )
    # Add test_agent_type column to jobs
    op.add_column(
        "jobs",
        sa.Column(
            "test_agent_type",
            sa.String(50),
            nullable=False,
            server_default="generic_testing",
        ),
    )
    # Add updated_at column to jobs
    op.add_column(
        "jobs",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    # Change jobs.status server_default from 'queued' to 'pending'
    op.alter_column(
        "jobs",
        "status",
        existing_type=sa.String(20),
        server_default="pending",
        existing_nullable=False,
    )
    # Create settings table
    op.create_table(
        "settings",
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("settings")
    op.alter_column(
        "jobs",
        "status",
        existing_type=sa.String(20),
        server_default="queued",
        existing_nullable=False,
    )
    op.drop_column("jobs", "updated_at")
    op.drop_column("jobs", "test_agent_type")
    op.drop_column("jobs", "dev_agent_type")
