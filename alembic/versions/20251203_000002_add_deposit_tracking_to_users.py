"""Add deposit tracking fields to users.

Revision ID: 20251203_000002
Revises: 20251203_000001
Create Date: 2025-12-03

Adds fields for automatic deposit detection from blockchain.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251203_000002'
down_revision = '20251203_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add deposit tracking columns to users table."""
    # Total deposited USDT (from blockchain scan)
    op.add_column(
        'users',
        sa.Column(
            'total_deposited_usdt',
            sa.DECIMAL(precision=18, scale=8),
            nullable=False,
            server_default='0',
            comment='Total USDT deposited to system wallet from user wallet'
        )
    )
    
    # Active depositor flag (>= 30 USDT)
    op.add_column(
        'users',
        sa.Column(
            'is_active_depositor',
            sa.Boolean(),
            nullable=False,
            server_default='false',
            comment='True if total_deposited_usdt >= 30 USDT'
        )
    )
    
    # Last scan timestamp
    op.add_column(
        'users',
        sa.Column(
            'last_deposit_scan_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Last time deposits were scanned from blockchain'
        )
    )
    
    # Deposit transaction count
    op.add_column(
        'users',
        sa.Column(
            'deposit_tx_count',
            sa.Integer(),
            nullable=False,
            server_default='0',
            comment='Number of deposit transactions found'
        )
    )
    
    # Create index for active depositor queries
    op.create_index(
        'ix_users_is_active_depositor',
        'users',
        ['is_active_depositor']
    )


def downgrade() -> None:
    """Remove deposit tracking columns from users table."""
    op.drop_index('ix_users_is_active_depositor', table_name='users')
    op.drop_column('users', 'deposit_tx_count')
    op.drop_column('users', 'last_deposit_scan_at')
    op.drop_column('users', 'is_active_depositor')
    op.drop_column('users', 'total_deposited_usdt')

