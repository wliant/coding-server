"""Add required_capabilities, assigned_sandbox_id, assigned_sandbox_url to jobs table.

Revision ID: 0014
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY


revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("required_capabilities", ARRAY(sa.Text()), nullable=True))
    op.add_column("jobs", sa.Column("assigned_sandbox_id", sa.String(255), nullable=True))
    op.add_column("jobs", sa.Column("assigned_sandbox_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "assigned_sandbox_url")
    op.drop_column("jobs", "assigned_sandbox_id")
    op.drop_column("jobs", "required_capabilities")
