"""add action_type and appeal_deadline to blacklist

Revision ID: add_blacklist_action_type
Revises: add_phone_email
Create Date: 2025-01-01 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_blacklist_action_type'
down_revision: Union[str, None] = 'add_phone_email'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add action_type column
    op.add_column('blacklist', sa.Column('action_type', sa.String(length=50), nullable=False, server_default='registration_denied'))
    
    # Add appeal_deadline column
    op.add_column('blacklist', sa.Column('appeal_deadline', sa.DateTime(timezone=True), nullable=True))
    
    # Add is_active column if it doesn't exist
    try:
        op.add_column('blacklist', sa.Column('is_active', sa.Integer(), nullable=False, server_default='1'))
    except Exception:
        # Column might already exist
        pass
    
    # Add created_at column if it doesn't exist
    try:
        op.add_column('blacklist', sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    except Exception:
        # Column might already exist
        pass
    
    # Create index on action_type
    op.create_index('ix_blacklist_action_type', 'blacklist', ['action_type'])


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_blacklist_action_type', table_name='blacklist')
    
    # Remove columns
    op.drop_column('blacklist', 'created_at')
    op.drop_column('blacklist', 'is_active')
    op.drop_column('blacklist', 'appeal_deadline')
    op.drop_column('blacklist', 'action_type')

