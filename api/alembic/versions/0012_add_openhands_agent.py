"""Add openhands_agent to agents table.

Revision ID: 0012
Revises: 0011
Create Date: 2026-03-11
"""

from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    agents_table = sa.table(
        "agents",
        sa.column("identifier", sa.String),
        sa.column("display_name", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        agents_table,
        [
            {
                "identifier": "openhands_agent",
                "display_name": "OpenHands Agent",
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM agents WHERE identifier = 'openhands_agent'")
