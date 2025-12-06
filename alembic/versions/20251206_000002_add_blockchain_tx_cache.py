"""Add blockchain transaction cache table.

Revision ID: 20251206_000002
Revises: 20251206_000001
Create Date: 2025-12-06

This migration adds a table for caching blockchain transactions
to avoid repeated RPC calls to QuickNode/NodeReal.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20251206_000002"
down_revision = "20251206_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create blockchain_tx_cache table."""
    op.create_table(
        "blockchain_tx_cache",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        # Transaction identification
        sa.Column("tx_hash", sa.String(length=66), nullable=False),
        sa.Column("block_number", sa.BigInteger(), nullable=False),
        sa.Column("block_timestamp", sa.DateTime(timezone=True), nullable=True),
        # Addresses
        sa.Column("from_address", sa.String(length=42), nullable=False),
        sa.Column("to_address", sa.String(length=42), nullable=False),
        # Token info
        sa.Column("token_type", sa.String(length=20), nullable=False),  # USDT, PLEX, BNB
        sa.Column("token_address", sa.String(length=42), nullable=True),  # null for native BNB
        # Amount
        sa.Column("amount", sa.DECIMAL(precision=36, scale=18), nullable=False),
        sa.Column("amount_raw", sa.String(length=100), nullable=True),  # raw wei value
        # Direction relative to system wallet
        sa.Column("direction", sa.String(length=20), nullable=False),  # incoming, outgoing, internal
        # Status
        sa.Column("status", sa.String(length=20), nullable=False, default="confirmed"),
        sa.Column("confirmations", sa.Integer(), nullable=True),
        # Linking to our system entities
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("deposit_id", sa.Integer(), nullable=True),
        sa.Column("withdrawal_id", sa.Integer(), nullable=True),
        # Processing flags
        sa.Column("is_processed", sa.Boolean(), nullable=False, default=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_notes", sa.Text(), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Primary key
        sa.PrimaryKeyConstraint("id"),
        # Unique constraint on tx_hash to prevent duplicates
        sa.UniqueConstraint("tx_hash", name="uq_blockchain_tx_cache_tx_hash"),
    )

    # Create indexes for fast lookups
    op.create_index(
        "idx_blockchain_tx_cache_from_address",
        "blockchain_tx_cache",
        ["from_address"],
    )
    op.create_index(
        "idx_blockchain_tx_cache_to_address",
        "blockchain_tx_cache",
        ["to_address"],
    )
    op.create_index(
        "idx_blockchain_tx_cache_block_number",
        "blockchain_tx_cache",
        ["block_number"],
    )
    op.create_index(
        "idx_blockchain_tx_cache_token_type",
        "blockchain_tx_cache",
        ["token_type"],
    )
    op.create_index(
        "idx_blockchain_tx_cache_direction",
        "blockchain_tx_cache",
        ["direction"],
    )
    op.create_index(
        "idx_blockchain_tx_cache_user_id",
        "blockchain_tx_cache",
        ["user_id"],
    )
    op.create_index(
        "idx_blockchain_tx_cache_is_processed",
        "blockchain_tx_cache",
        ["is_processed"],
    )
    # Composite index for common queries
    op.create_index(
        "idx_blockchain_tx_cache_addr_token",
        "blockchain_tx_cache",
        ["from_address", "to_address", "token_type"],
    )

    # Add last_scanned_block to global_settings for tracking scan progress
    op.add_column(
        "global_settings",
        sa.Column(
            "last_scanned_block_usdt",
            sa.BigInteger(),
            nullable=True,
            default=0,
        ),
    )
    op.add_column(
        "global_settings",
        sa.Column(
            "last_scanned_block_plex",
            sa.BigInteger(),
            nullable=True,
            default=0,
        ),
    )


def downgrade() -> None:
    """Drop blockchain_tx_cache table."""
    op.drop_column("global_settings", "last_scanned_block_plex")
    op.drop_column("global_settings", "last_scanned_block_usdt")

    op.drop_index("idx_blockchain_tx_cache_addr_token", table_name="blockchain_tx_cache")
    op.drop_index("idx_blockchain_tx_cache_is_processed", table_name="blockchain_tx_cache")
    op.drop_index("idx_blockchain_tx_cache_user_id", table_name="blockchain_tx_cache")
    op.drop_index("idx_blockchain_tx_cache_direction", table_name="blockchain_tx_cache")
    op.drop_index("idx_blockchain_tx_cache_token_type", table_name="blockchain_tx_cache")
    op.drop_index("idx_blockchain_tx_cache_block_number", table_name="blockchain_tx_cache")
    op.drop_index("idx_blockchain_tx_cache_to_address", table_name="blockchain_tx_cache")
    op.drop_index("idx_blockchain_tx_cache_from_address", table_name="blockchain_tx_cache")

    op.drop_table("blockchain_tx_cache")
