"""Make reward_session_id nullable for individual accruals.

Revision ID: 20251213_014500
Revises: 20251212_230000
Create Date: 2025-12-13 01:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251213_014500'
down_revision = '20251210_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Make reward_session_id nullable for individual reward accruals."""
    # Drop the existing constraint that depends on reward_session_id
    op.drop_constraint(
        'uq_deposit_reward_deposit_session',
        'deposit_rewards',
        type_='unique'
    )

    # Drop foreign key constraint first
    op.drop_constraint(
        'deposit_rewards_reward_session_id_fkey',
        'deposit_rewards',
        type_='foreignkey'
    )

    # Alter column to be nullable
    op.alter_column(
        'deposit_rewards',
        'reward_session_id',
        existing_type=sa.Integer(),
        nullable=True
    )

    # Recreate foreign key allowing nulls
    op.create_foreign_key(
        'deposit_rewards_reward_session_id_fkey',
        'deposit_rewards',
        'reward_sessions',
        ['reward_session_id'],
        ['id']
    )

    # Create a partial unique constraint that only applies when session_id is not null
    # For PostgreSQL, we use a unique index with a WHERE clause
    op.execute("""
        CREATE UNIQUE INDEX uq_deposit_reward_deposit_session
        ON deposit_rewards (deposit_id, reward_session_id)
        WHERE reward_session_id IS NOT NULL
    """)

    # Note: For individual accruals (where reward_session_id IS NULL),
    # duplicate prevention is handled by application logic that checks
    # next_accrual_at timestamp. No additional unique index needed.


def downgrade() -> None:
    """Revert changes - make reward_session_id required again."""
    # Drop the partial unique indexes
    op.execute("DROP INDEX IF EXISTS uq_deposit_reward_individual_daily")
    op.execute("DROP INDEX IF EXISTS uq_deposit_reward_deposit_session")

    # Drop foreign key
    op.drop_constraint(
        'deposit_rewards_reward_session_id_fkey',
        'deposit_rewards',
        type_='foreignkey'
    )

    # Make column not nullable (set existing nulls to 0 first - will fail if data exists)
    op.alter_column(
        'deposit_rewards',
        'reward_session_id',
        existing_type=sa.Integer(),
        nullable=False
    )

    # Recreate foreign key
    op.create_foreign_key(
        'deposit_rewards_reward_session_id_fkey',
        'deposit_rewards',
        'reward_sessions',
        ['reward_session_id'],
        ['id']
    )

    # Recreate original unique constraint
    op.create_unique_constraint(
        'uq_deposit_reward_deposit_session',
        'deposit_rewards',
        ['deposit_id', 'reward_session_id']
    )
