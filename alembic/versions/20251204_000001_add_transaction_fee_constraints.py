"""Add fee validation constraints to transactions.

Revision ID: 20251204_000001
Revises: 20251203_000003
Create Date: 2025-12-04

This migration adds database-level constraints to ensure:
1. Fee is always less than amount (fee < amount)
2. Fee is non-negative (fee >= 0)
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = '20251204_000001'
down_revision = '20251203_000003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add fee validation constraints."""
    # Add constraint: fee must be less than amount
    op.create_check_constraint(
        'check_transaction_fee_less_than_amount',
        'transactions',
        'fee < amount'
    )

    # Add constraint: fee must be non-negative
    op.create_check_constraint(
        'check_transaction_fee_non_negative',
        'transactions',
        'fee >= 0'
    )


def downgrade() -> None:
    """Remove fee validation constraints."""
    op.drop_constraint(
        'check_transaction_fee_less_than_amount',
        'transactions',
        type_='check'
    )

    op.drop_constraint(
        'check_transaction_fee_non_negative',
        'transactions',
        type_='check'
    )
