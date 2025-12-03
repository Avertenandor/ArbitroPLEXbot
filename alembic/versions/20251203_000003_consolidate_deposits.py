"""Consolidate deposits and add work status tracking.

Revision ID: 20251203_000003
Revises: 20251203_000002
Create Date: 2025-12-03

This migration:
1. Adds deposit consolidation fields
2. Adds user work status fields for PLEX monitoring
3. Consolidates existing deposits per user into single deposits
4. Updates PLEX payment requirements for "pay first, work after" model
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from decimal import Decimal


# revision identifiers, used by Alembic.
revision = '20251203_000003'
down_revision = '20251203_000002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add consolidation and work status fields, consolidate existing deposits."""

    # ========== 1. Add fields to deposits table ==========

    # Consolidated deposit flag
    op.add_column(
        'deposits',
        sa.Column(
            'is_consolidated',
            sa.Boolean(),
            nullable=False,
            server_default='false',
            comment='True if this deposit was created by consolidating multiple transactions'
        )
    )

    # Consolidated at timestamp
    op.add_column(
        'deposits',
        sa.Column(
            'consolidated_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='When this deposit was consolidated'
        )
    )

    # Original transaction hashes for consolidated deposits (JSON array)
    op.add_column(
        'deposits',
        sa.Column(
            'consolidated_tx_hashes',
            JSONB,
            nullable=True,
            comment='Original tx hashes if consolidated from multiple transactions'
        )
    )

    # Individual 24-hour cycle start for PLEX payment
    op.add_column(
        'deposits',
        sa.Column(
            'plex_cycle_start',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Start of individual 24h PLEX payment cycle for this deposit'
        )
    )

    # ========== 2. Add fields to users table ==========

    # Work status: active, suspended_no_plex, suspended_no_payment
    op.add_column(
        'users',
        sa.Column(
            'work_status',
            sa.String(50),
            nullable=False,
            server_default='active',
            comment='Work status: active, suspended_no_plex, suspended_no_payment'
        )
    )

    # Last PLEX balance check timestamp
    op.add_column(
        'users',
        sa.Column(
            'last_plex_check_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Last time PLEX balance was checked'
        )
    )

    # Last checked PLEX balance value
    op.add_column(
        'users',
        sa.Column(
            'last_plex_balance',
            sa.DECIMAL(precision=18, scale=8),
            nullable=True,
            comment='Last checked PLEX balance on wallet'
        )
    )

    # When PLEX balance became insufficient
    op.add_column(
        'users',
        sa.Column(
            'plex_insufficient_since',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='When PLEX balance first dropped below minimum'
        )
    )

    # Flag that existing deposits were already consolidated
    op.add_column(
        'users',
        sa.Column(
            'deposits_consolidated',
            sa.Boolean(),
            nullable=False,
            server_default='false',
            comment='True if pre-existing deposits were consolidated'
        )
    )

    # Create index for work status filtering
    op.create_index(
        'ix_users_work_status',
        'users',
        ['work_status']
    )

    # ========== 3. Add fields to plex_payment_requirements ==========

    # Is deposit active for work (PLEX paid in advance)
    op.add_column(
        'plex_payment_requirements',
        sa.Column(
            'is_work_active',
            sa.Boolean(),
            nullable=False,
            server_default='false',
            comment='True if PLEX payment received, deposit can work'
        )
    )

    # First payment received timestamp
    op.add_column(
        'plex_payment_requirements',
        sa.Column(
            'first_payment_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='When first PLEX payment was received (starts work)'
        )
    )

    # ========== 4. Consolidate existing deposits (data migration) ==========
    # This is done via a separate Python script to handle complex logic
    # The consolidation will:
    # - Sum all confirmed deposits per user
    # - Create one consolidated deposit with total amount
    # - Archive old deposits (mark as consolidated_into)
    # - Create PLEX payment requirement for consolidated deposit

    # Note: Actual data migration is done in consolidate_existing_deposits.py script
    # which should be run after this migration


def downgrade() -> None:
    """Remove consolidation and work status fields."""

    # Remove plex_payment_requirements columns
    op.drop_column('plex_payment_requirements', 'first_payment_at')
    op.drop_column('plex_payment_requirements', 'is_work_active')

    # Remove users columns
    op.drop_index('ix_users_work_status', table_name='users')
    op.drop_column('users', 'deposits_consolidated')
    op.drop_column('users', 'plex_insufficient_since')
    op.drop_column('users', 'last_plex_balance')
    op.drop_column('users', 'last_plex_check_at')
    op.drop_column('users', 'work_status')

    # Remove deposits columns
    op.drop_column('deposits', 'plex_cycle_start')
    op.drop_column('deposits', 'consolidated_tx_hashes')
    op.drop_column('deposits', 'consolidated_at')
    op.drop_column('deposits', 'is_consolidated')
