"""add wallet_address to blacklist

Revision ID: 20250118_000001
Revises: 20250113_000002
Create Date: 2025-01-18 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250118_000001'
down_revision: Union[str, None] = '20250113_000002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make telegram_id nullable and remove unique constraint
    # (to support wallet-only bans)
    
    # Drop unique constraint on telegram_id if it exists
    # (Safe drop - check if exists first)
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    constraints = [
        c['name'] for c in inspector.get_unique_constraints('blacklist')
    ]
    if 'blacklist_telegram_id_key' in constraints:
        op.drop_constraint('blacklist_telegram_id_key', 'blacklist', type_='unique')
    
    op.alter_column(
        'blacklist',
        'telegram_id',
        existing_type=sa.BigInteger(),
        nullable=True,
        existing_nullable=False
    )
    
    # Add wallet_address column
    op.add_column(
        'blacklist',
        sa.Column('wallet_address', sa.String(length=42), nullable=True)
    )
    
    # Create index on wallet_address
    op.create_index(
        'ix_blacklist_wallet_address',
        'blacklist',
        ['wallet_address']
    )


def downgrade() -> None:
    # Drop index on wallet_address
    op.drop_index('ix_blacklist_wallet_address', table_name='blacklist')
    
    # Remove wallet_address column
    op.drop_column('blacklist', 'wallet_address')
    
    # Restore unique constraint on telegram_id
    op.create_unique_constraint('blacklist_telegram_id_key', 'blacklist', ['telegram_id'])
    
    # Make telegram_id not nullable again
    op.alter_column(
        'blacklist',
        'telegram_id',
        existing_type=sa.BigInteger(),
        nullable=False,
        existing_nullable=True
    )

