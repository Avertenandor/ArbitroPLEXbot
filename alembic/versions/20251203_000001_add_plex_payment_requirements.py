"""Add plex_payment_requirements table.

Revision ID: 20251203_000001
Revises: 20251130_000004_add_roi_notifications
Create Date: 2025-12-03

Tracks daily PLEX payment requirements for each deposit.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251203_000001'
down_revision = '20251130_roi_notif'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create plex_payment_requirements table."""
    op.create_table(
        'plex_payment_requirements',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('deposit_id', sa.Integer(), nullable=False),
        sa.Column(
            'daily_plex_required',
            sa.DECIMAL(precision=18, scale=8),
            nullable=False,
            comment='Daily PLEX payment required (deposit_amount * 10)'
        ),
        sa.Column(
            'next_payment_due',
            sa.DateTime(timezone=True),
            nullable=False,
            comment='Next payment due (deposit_created_at + 24h)'
        ),
        sa.Column(
            'warning_due',
            sa.DateTime(timezone=True),
            nullable=False,
            comment='Warning will be sent at this time (deposit_created_at + 25h)'
        ),
        sa.Column(
            'block_due',
            sa.DateTime(timezone=True),
            nullable=False,
            comment='Block at this time if not paid (deposit_created_at + 49h)'
        ),
        sa.Column(
            'status',
            sa.String(length=20),
            nullable=False,
            server_default='active',
            comment='active, warning, blocked, paid'
        ),
        sa.Column(
            'last_payment_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Last successful PLEX payment timestamp'
        ),
        sa.Column(
            'last_payment_tx_hash',
            sa.String(length=255),
            nullable=True,
            comment='Last payment transaction hash'
        ),
        sa.Column(
            'total_paid_plex',
            sa.DECIMAL(precision=18, scale=8),
            nullable=False,
            server_default='0',
            comment='Total PLEX paid for this deposit'
        ),
        sa.Column(
            'days_paid',
            sa.Integer(),
            nullable=False,
            server_default='0',
            comment='Number of days paid for this deposit'
        ),
        sa.Column(
            'warning_sent_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='When warning was sent'
        ),
        sa.Column(
            'warning_count',
            sa.Integer(),
            nullable=False,
            server_default='0',
            comment='Number of warnings sent'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('now()')
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('now()')
        ),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['deposit_id'],
            ['deposits.id'],
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            'daily_plex_required > 0',
            name='check_plex_daily_required_positive'
        )
    )
    
    # Create indexes
    op.create_index(
        'ix_plex_payment_requirements_user_id',
        'plex_payment_requirements',
        ['user_id']
    )
    op.create_index(
        'ix_plex_payment_requirements_deposit_id',
        'plex_payment_requirements',
        ['deposit_id'],
        unique=True
    )
    op.create_index(
        'ix_plex_payment_requirements_status',
        'plex_payment_requirements',
        ['status']
    )
    op.create_index(
        'ix_plex_payment_requirements_next_payment_due',
        'plex_payment_requirements',
        ['next_payment_due']
    )


def downgrade() -> None:
    """Drop plex_payment_requirements table."""
    op.drop_index(
        'ix_plex_payment_requirements_next_payment_due',
        table_name='plex_payment_requirements'
    )
    op.drop_index(
        'ix_plex_payment_requirements_status',
        table_name='plex_payment_requirements'
    )
    op.drop_index(
        'ix_plex_payment_requirements_deposit_id',
        table_name='plex_payment_requirements'
    )
    op.drop_index(
        'ix_plex_payment_requirements_user_id',
        table_name='plex_payment_requirements'
    )
    op.drop_table('plex_payment_requirements')

