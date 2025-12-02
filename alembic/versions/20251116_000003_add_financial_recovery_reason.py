# MCP-MARKER:CREATE:ADD_FINANCIAL_RECOVERY_REASON
# MCP-ANCHOR: add-financial-recovery-reason
# MCP-DEPS: [alembic, sqlalchemy]
# MCP-PROVIDES: upgrade(), downgrade()
# MCP-SUMMARY: Adds reason and timestamp columns to the
# financial_password_recovery table.
"""add reason and timestamps to financial_password_recovery

Revision ID: add_finpass_reason
Revises: create_appeals_table
Create Date: 2025-11-16 00:00:03.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_finpass_reason'
down_revision: Union[str, None] = 'create_appeals_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add user-provided reason column
    op.add_column(
        'financial_password_recovery',
        sa.Column(
            'reason',
            sa.Text(),
            nullable=False,
            server_default='Reason not provided',
        ),
    )

    # Add audit timestamps
    op.add_column(
        'financial_password_recovery',
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.add_column(
        'financial_password_recovery',
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Drop the temporary defaults after the columns are populated
    op.alter_column(
        'financial_password_recovery',
        'reason',
        server_default=None,
    )
    op.alter_column(
        'financial_password_recovery',
        'created_at',
        server_default=None,
    )
    op.alter_column(
        'financial_password_recovery',
        'updated_at',
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column('financial_password_recovery', 'updated_at')
    op.drop_column('financial_password_recovery', 'created_at')
    op.drop_column('financial_password_recovery', 'reason')
