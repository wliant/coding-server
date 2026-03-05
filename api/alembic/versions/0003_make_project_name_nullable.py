"""make project name nullable

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-04 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("projects", "name", existing_type=sa.String(255), nullable=True)


def downgrade() -> None:
    op.alter_column("projects", "name", existing_type=sa.String(255), nullable=False)
