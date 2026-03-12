"""add task_type and commits_to_review to jobs

Revision ID: 0011
Revises: 0010
Create Date: 2026-03-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("task_type", sa.String(30), nullable=True))
    op.add_column("jobs", sa.Column("commits_to_review", sa.Integer(), nullable=True))

    # Backfill: scaffold_project for new projects, build_feature for the rest
    op.execute(
        "UPDATE jobs SET task_type = 'scaffold_project' "
        "WHERE project_id IN (SELECT id FROM projects WHERE source_type = 'new')"
    )
    op.execute(
        "UPDATE jobs SET task_type = 'build_feature' WHERE task_type IS NULL"
    )

    op.alter_column("jobs", "task_type", nullable=False, server_default="build_feature")


def downgrade() -> None:
    op.drop_column("jobs", "commits_to_review")
    op.drop_column("jobs", "task_type")
