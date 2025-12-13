"""Add bonus_credit_id to plex_payment_requirements.

Revision ID: 20251213_030000
Revises: 20251213_014500
Create Date: 2025-12-13

This migration allows plex_payment_requirements to track both
deposits and bonus credits for PLEX payment obligations.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251213_030000"
down_revision = "20251213_014500"
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
    # Use raw SQL with IF EXISTS to handle case when constraint doesn't exist
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'ix_plex_payment_requirements_deposit_id'
            ) THEN
                ALTER TABLE plex_payment_requirements
                DROP CONSTRAINT ix_plex_payment_requirements_deposit_id;
            END IF;
        END $$;
    """)

    # Also try to drop as index
    op.execute("""
        DROP INDEX IF EXISTS ix_plex_payment_requirements_deposit_id;
    """)

    # 3. Add bonus_credit_id column (if not exists)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'plex_payment_requirements'
                AND column_name = 'bonus_credit_id'
            ) THEN
                ALTER TABLE plex_payment_requirements
                ADD COLUMN bonus_credit_id INTEGER;
            END IF;
        END $$;
    """)

    # Add foreign key constraint if not exists
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'plex_payment_requirements_bonus_credit_id_fkey'
            ) THEN
                ALTER TABLE plex_payment_requirements
                ADD CONSTRAINT plex_payment_requirements_bonus_credit_id_fkey
                FOREIGN KEY (bonus_credit_id) REFERENCES bonus_credits(id) ON DELETE CASCADE;
            END IF;
        END $$;
    """)

    # 4. Create partial unique indexes (if not exists)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_plex_payment_requirements_deposit_id
        ON plex_payment_requirements (deposit_id)
        WHERE deposit_id IS NOT NULL;
    """)

    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_plex_payment_requirements_bonus_credit_id
        ON plex_payment_requirements (bonus_credit_id)
        WHERE bonus_credit_id IS NOT NULL;
    """)

    # 5. Add check constraint: at least one of deposit_id or bonus_credit_id must be set
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'check_deposit_or_bonus'
            ) THEN
                ALTER TABLE plex_payment_requirements
                ADD CONSTRAINT check_deposit_or_bonus
                CHECK (deposit_id IS NOT NULL OR bonus_credit_id IS NOT NULL);
            END IF;
        END $$;
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
