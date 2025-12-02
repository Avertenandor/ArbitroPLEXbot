"""create appeals table

Revision ID: create_appeals_table
Revises: add_blacklist_action_type
Create Date: 2025-01-01 00:00:02.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'create_appeals_table'
down_revision: Union[str, None] = 'add_blacklist_action_type'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create appeals table
    op.create_table(
        'appeals',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('blacklist_id', sa.Integer(), nullable=False),
        sa.Column('appeal_text', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('reviewed_by_admin_id', sa.BigInteger(), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['blacklist_id'], ['blacklist.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by_admin_id'], ['admins.id'], ondelete='SET NULL'),
    )
    
    # Create indexes
    op.create_index('ix_appeals_user_id', 'appeals', ['user_id'])
    op.create_index('ix_appeals_blacklist_id', 'appeals', ['blacklist_id'])
    op.create_index('ix_appeals_status', 'appeals', ['status'])
    op.create_index('ix_appeals_created_at', 'appeals', ['created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_appeals_created_at', table_name='appeals')
    op.drop_index('ix_appeals_status', table_name='appeals')
    op.drop_index('ix_appeals_blacklist_id', table_name='appeals')
    op.drop_index('ix_appeals_user_id', table_name='appeals')
    
    # Drop table
    op.drop_table('appeals')

