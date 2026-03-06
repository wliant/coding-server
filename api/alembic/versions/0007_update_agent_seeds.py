"""Update agent seeds to match available agent implementations.

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-07
"""

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Deactivate legacy seed agents (preserves FK references from existing jobs)
    op.execute(
        "UPDATE agents SET is_active = false "
        "WHERE identifier IN ('spec_driven_development', 'generic_testing')"
    )

    # Insert the three real agent implementations
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
                "identifier": "crewai_coding_team",
                "display_name": "CrewAI Coding Team",
                "is_active": True,
            },
            {
                "identifier": "simple_crewai_pair_agent",
                "display_name": "Simple CrewAI Pair Agent",
                "is_active": True,
            },
            {
                "identifier": "simple_langchain_deepagent",
                "display_name": "Simple Langchain Deep Agent",
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM agents "
        "WHERE identifier IN "
        "('crewai_coding_team', 'simple_crewai_pair_agent', 'simple_langchain_deepagent')"
    )
    op.execute(
        "UPDATE agents SET is_active = true "
        "WHERE identifier IN ('spec_driven_development', 'generic_testing')"
    )
