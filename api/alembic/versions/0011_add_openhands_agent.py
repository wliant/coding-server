"""Add openhands_agent to agents table.

Revision ID: 0011
Revises: 0010
Create Date: 2026-03-11
"""

from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
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
