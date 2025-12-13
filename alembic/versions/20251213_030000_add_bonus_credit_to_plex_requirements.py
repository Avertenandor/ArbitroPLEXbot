"""Add bonus_credit_id to plex_payment_requirements.

Revision ID: 20251213_030000
Revises: 
Create Date: 2025-12-13

This migration allows plex_payment_requirements to track both
deposits and bonus credits for PLEX payment obligations.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251213_030000"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Make deposit_id nullable (to allow bonus-only records)
    op.alter_column(
        "plex_payment_requirements",
        "deposit_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    
    # 2. Drop unique constraint on deposit_id (will recreate as partial unique)
    op.drop_constraint(
        "ix_plex_payment_requirements_deposit_id",
        "plex_payment_requirements",
        type_="unique"
    )
    
    # 3. Add bonus_credit_id column
    op.add_column(
        "plex_payment_requirements",
        sa.Column(
            "bonus_credit_id",
            sa.Integer(),
            sa.ForeignKey("bonus_credits.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
    )
    
    # 4. Create partial unique indexes
    op.create_index(
        "ix_plex_payment_requirements_deposit_id",
        "plex_payment_requirements",
        ["deposit_id"],
        unique=True,
        postgresql_where=sa.text("deposit_id IS NOT NULL"),
    )
    
    op.create_index(
        "ix_plex_payment_requirements_bonus_credit_id",
        "plex_payment_requirements",
        ["bonus_credit_id"],
        unique=True,
        postgresql_where=sa.text("bonus_credit_id IS NOT NULL"),
    )
    
    # 5. Add check constraint: at least one of deposit_id or bonus_credit_id must be set
    op.execute("""
        ALTER TABLE plex_payment_requirements
        ADD CONSTRAINT check_deposit_or_bonus
        CHECK (deposit_id IS NOT NULL OR bonus_credit_id IS NOT NULL)
    """)


def downgrade() -> None:
    # Remove check constraint
    op.execute("""
        ALTER TABLE plex_payment_requirements
        DROP CONSTRAINT IF EXISTS check_deposit_or_bonus
    """)
    
    # Remove bonus_credit_id column and indexes
    op.drop_index("ix_plex_payment_requirements_bonus_credit_id", "plex_payment_requirements")
    op.drop_column("plex_payment_requirements", "bonus_credit_id")
    
    # Restore deposit_id as not nullable and unique
    op.drop_index("ix_plex_payment_requirements_deposit_id", "plex_payment_requirements")
    
    # Delete any records without deposit_id before making it NOT NULL
    op.execute("DELETE FROM plex_payment_requirements WHERE deposit_id IS NULL")
    
    op.alter_column(
        "plex_payment_requirements",
        "deposit_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    
    op.create_index(
        "ix_plex_payment_requirements_deposit_id",
        "plex_payment_requirements",
        ["deposit_id"],
        unique=True,
    )
