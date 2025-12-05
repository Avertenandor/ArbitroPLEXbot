"""Create sponsor_inquiries table

Revision ID: 20251205_000001
Revises: 
Create Date: 2025-12-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251205_000001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sponsor_inquiries table
    op.create_table(
        'sponsor_inquiries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('referral_id', sa.Integer(), nullable=False),
        sa.Column('referral_telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('sponsor_id', sa.Integer(), nullable=False),
        sa.Column('sponsor_telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('initial_question', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='new'),
        sa.Column('is_read_by_sponsor', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_read_by_referral', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_by', sa.String(20), nullable=True),
        sa.ForeignKeyConstraint(['referral_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['sponsor_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sponsor_inquiries_referral_id', 'sponsor_inquiries', ['referral_id'])
    op.create_index('ix_sponsor_inquiries_sponsor_id', 'sponsor_inquiries', ['sponsor_id'])
    op.create_index('ix_sponsor_inquiries_status', 'sponsor_inquiries', ['status'])

    # Create sponsor_inquiry_messages table
    op.create_table(
        'sponsor_inquiry_messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('inquiry_id', sa.Integer(), nullable=False),
        sa.Column('sender_type', sa.String(20), nullable=False),
        sa.Column('message_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['inquiry_id'], ['sponsor_inquiries.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sponsor_inquiry_messages_inquiry_id', 'sponsor_inquiry_messages', ['inquiry_id'])


def downgrade() -> None:
    op.drop_index('ix_sponsor_inquiry_messages_inquiry_id', 'sponsor_inquiry_messages')
    op.drop_table('sponsor_inquiry_messages')
    
    op.drop_index('ix_sponsor_inquiries_status', 'sponsor_inquiries')
    op.drop_index('ix_sponsor_inquiries_sponsor_id', 'sponsor_inquiries')
    op.drop_index('ix_sponsor_inquiries_referral_id', 'sponsor_inquiries')
    op.drop_table('sponsor_inquiries')
