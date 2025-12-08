"""Add user_activities table for comprehensive activity logging.

Revision ID: 20251208_000002_add_user_activities
Revises: 20251208_000001_add_bonus_credits
Create Date: 2025-12-08

"""

from datetime import UTC, datetime
from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20251208_000002_add_user_activities"
down_revision: str | None = "20251208_000001_add_bonus_credits"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create user_activities table."""
    op.create_table(
        "user_activities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("activity_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("message_text", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for fast queries
    op.create_index(
        "ix_user_activities_telegram_id",
        "user_activities",
        ["telegram_id"],
    )
    op.create_index(
        "ix_user_activities_activity_type",
        "user_activities",
        ["activity_type"],
    )
    op.create_index(
        "ix_user_activities_created_at",
        "user_activities",
        ["created_at"],
    )
    op.create_index(
        "ix_user_activities_user_id_created",
        "user_activities",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_user_activities_type_created",
        "user_activities",
        ["activity_type", "created_at"],
    )


def downgrade() -> None:
    """Drop user_activities table."""
    op.drop_index("ix_user_activities_type_created", table_name="user_activities")
    op.drop_index("ix_user_activities_user_id_created", table_name="user_activities")
    op.drop_index("ix_user_activities_created_at", table_name="user_activities")
    op.drop_index("ix_user_activities_activity_type", table_name="user_activities")
    op.drop_index("ix_user_activities_telegram_id", table_name="user_activities")
    op.drop_table("user_activities")
