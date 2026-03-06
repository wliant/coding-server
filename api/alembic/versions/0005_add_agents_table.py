"""add agents table

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-06 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    agents_table = op.create_table(
        "agents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("identifier", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("identifier"),
    )
    op.bulk_insert(
        agents_table,
        [
            {
                "identifier": "spec_driven_development",
                "display_name": "Spec-Driven Development",
                "is_active": True,
            },
            {
                "identifier": "generic_testing",
                "display_name": "Generic Testing",
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("agents")
