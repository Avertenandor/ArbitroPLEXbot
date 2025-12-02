"""add phone and email to users

Revision ID: add_phone_email
Revises: 
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_phone_email'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add phone and email columns to users table
    op.add_column('users', sa.Column('phone', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('email', sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Remove phone and email columns from users table
    op.drop_column('users', 'email')
    op.drop_column('users', 'phone')

