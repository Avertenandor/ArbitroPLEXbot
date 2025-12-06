"""create blockchain_sync_state table

Revision ID: 20251206_create_blockchain_sync_state
Revises: 
Create Date: 2025-12-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251206_create_blockchain_sync_state'
down_revision: Union[str, None] = '20251206_000002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create blockchain_sync_state table."""
    op.create_table(
        'blockchain_sync_state',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('token_type', sa.String(20), nullable=False),
        sa.Column('first_synced_block', sa.BigInteger(), nullable=False, default=0),
        sa.Column('last_synced_block', sa.BigInteger(), nullable=False, default=0),
        sa.Column('total_transactions', sa.Integer(), nullable=False, default=0),
        sa.Column('incoming_count', sa.Integer(), nullable=False, default=0),
        sa.Column('outgoing_count', sa.Integer(), nullable=False, default=0),
        sa.Column('full_sync_completed', sa.Boolean(), nullable=False, default=False),
        sa.Column('full_sync_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('full_sync_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('error_count', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Indexes
    op.create_index('ix_blockchain_sync_state_token_type', 'blockchain_sync_state', ['token_type'], unique=True)
    op.create_index('ix_blockchain_sync_state_last_synced_block', 'blockchain_sync_state', ['last_synced_block'])


def downgrade() -> None:
    """Drop blockchain_sync_state table."""
    op.drop_index('ix_blockchain_sync_state_last_synced_block', table_name='blockchain_sync_state')
    op.drop_index('ix_blockchain_sync_state_token_type', table_name='blockchain_sync_state')
    op.drop_table('blockchain_sync_state')
