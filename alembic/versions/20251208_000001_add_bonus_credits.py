"""Add bonus credits system.

Revision ID: 20251208_000001
Revises: 20250208_000001_plex_payment_reminder_fields
Create Date: 2025-12-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251208_000001'
down_revision: Union[str, None] = '20250208_000001_plex_payment_reminder_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add bonus_balance fields to users and create bonus_credits table."""
    
    # Add bonus fields to users table
    op.add_column(
        'users',
        sa.Column(
            'bonus_balance',
            sa.DECIMAL(18, 8),
            nullable=False,
            server_default='0',
            comment='Admin-granted bonus balance for ROI calculations'
        )
    )
    op.add_column(
        'users',
        sa.Column(
            'bonus_roi_earned',
            sa.DECIMAL(18, 8),
            nullable=False,
            server_default='0',
            comment='Total ROI earned from bonus credits'
        )
    )
    
    # Create bonus_credits table
    op.create_table(
        'bonus_credits',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('admin_id', sa.Integer(), nullable=True),
        sa.Column('amount', sa.DECIMAL(18, 8), nullable=False, comment='Original bonus amount in USDT equivalent'),
        sa.Column('roi_cap_multiplier', sa.DECIMAL(5, 2), nullable=False, server_default='5.00', comment='ROI cap multiplier (5.00 = 500%)'),
        sa.Column('roi_cap_amount', sa.DECIMAL(18, 8), nullable=False, comment='Maximum ROI that can be earned (amount * multiplier)'),
        sa.Column('roi_paid_amount', sa.DECIMAL(18, 8), nullable=False, server_default='0', comment='Total ROI already paid from this bonus'),
        sa.Column('next_accrual_at', sa.DateTime(timezone=True), nullable=True, comment='Next scheduled ROI accrual time'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', comment='Whether bonus is still active for ROI'),
        sa.Column('is_roi_completed', sa.Boolean(), nullable=False, server_default='false', comment='Whether ROI cap has been reached'),
        sa.Column('reason', sa.Text(), nullable=False, comment="Admin's reason for granting this bonus"),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True, comment='When ROI cap was reached'),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_by', sa.Integer(), nullable=True),
        sa.Column('cancel_reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['admin_id'], ['admins.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['cancelled_by'], ['admins.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_bonus_credits_user_active', 'bonus_credits', ['user_id', 'is_active'])
    op.create_index('idx_bonus_credits_admin', 'bonus_credits', ['admin_id'])
    op.create_index('idx_bonus_credits_user_id', 'bonus_credits', ['user_id'])
    op.create_index('idx_bonus_credits_next_accrual', 'bonus_credits', ['next_accrual_at'])


def downgrade() -> None:
    """Remove bonus credits system."""
    
    # Drop indexes
    op.drop_index('idx_bonus_credits_next_accrual', 'bonus_credits')
    op.drop_index('idx_bonus_credits_user_id', 'bonus_credits')
    op.drop_index('idx_bonus_credits_admin', 'bonus_credits')
    op.drop_index('idx_bonus_credits_user_active', 'bonus_credits')
    
    # Drop table
    op.drop_table('bonus_credits')
    
    # Remove columns from users
    op.drop_column('users', 'bonus_roi_earned')
    op.drop_column('users', 'bonus_balance')
