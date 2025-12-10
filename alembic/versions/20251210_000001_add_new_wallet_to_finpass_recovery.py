"""Add new_wallet_address to finpass recovery.

Revision ID: 20251210_000001
Revises: 20250608_000002
Create Date: 2025-12-10

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251210_000001"
down_revision = "20250608_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add new_wallet_address column to financial_password_recovery table."""
    op.add_column(
        "financial_password_recovery",
        sa.Column(
            "new_wallet_address",
            sa.String(255),
            nullable=True,
            comment="New wallet address if user requested wallet change during recovery",
        ),
    )


def downgrade() -> None:
    """Remove new_wallet_address column."""
    op.drop_column("financial_password_recovery", "new_wallet_address")
