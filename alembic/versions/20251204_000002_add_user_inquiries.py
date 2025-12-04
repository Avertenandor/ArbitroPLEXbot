"""Add user inquiries tables

Revision ID: 20251204_000002
Revises: 20251204_000001
Create Date: 2025-12-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251204_000002'
down_revision: Union[str, None] = '20251204_000001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_inquiries table
    op.create_table(
        'user_inquiries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('initial_question', sa.Text(), nullable=False),
        sa.Column(
            'status', sa.String(length=20),
            nullable=False, server_default='new'
        ),
        sa.Column('assigned_admin_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_by', sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(['assigned_admin_id'], ['admins.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        'ix_user_inquiries_user_id', 'user_inquiries',
        ['user_id'], unique=False
    )
    op.create_index(
        'ix_user_inquiries_telegram_id', 'user_inquiries',
        ['telegram_id'], unique=False
    )
    op.create_index(
        'ix_user_inquiries_status', 'user_inquiries', ['status'], unique=False
    )
    op.create_index(
        'ix_user_inquiries_assigned_admin_id', 'user_inquiries',
        ['assigned_admin_id'], unique=False
    )

    # Create inquiry_messages table
    op.create_table(
        'inquiry_messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('inquiry_id', sa.Integer(), nullable=False),
        sa.Column('sender_type', sa.String(length=20), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=False),
        sa.Column('message_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['inquiry_id'], ['user_inquiries.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        'ix_inquiry_messages_inquiry_id', 'inquiry_messages',
        ['inquiry_id'], unique=False
    )


def downgrade() -> None:
    op.drop_index(
        'ix_inquiry_messages_inquiry_id', table_name='inquiry_messages'
    )
    op.drop_table('inquiry_messages')
    op.drop_index(
        'ix_user_inquiries_assigned_admin_id', table_name='user_inquiries'
    )
    op.drop_index('ix_user_inquiries_status', table_name='user_inquiries')
    op.drop_index(
        'ix_user_inquiries_telegram_id', table_name='user_inquiries'
    )
    op.drop_index('ix_user_inquiries_user_id', table_name='user_inquiries')
    op.drop_table('user_inquiries')
