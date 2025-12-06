"""
Blockchain Transaction Cache model.

Caches all blockchain transactions involving our system wallet
to avoid repeated RPC calls to external providers.
"""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    DECIMAL,
    BigInteger,
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BlockchainTxCache(Base):
    """
    Blockchain transaction cache.

    Stores all discovered blockchain transactions for:
    - USDT transfers to/from system wallet
    - PLEX transfers to/from system wallet
    - BNB transfers (gas payments)

    This cache prevents repeated RPC calls and provides
    historical transaction data instantly.
    """

    __tablename__ = "blockchain_tx_cache"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Transaction identification
    tx_hash: Mapped[str] = mapped_column(
        String(66), nullable=False, unique=True, index=True
    )
    block_number: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    block_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Addresses (normalized to lowercase)
    from_address: Mapped[str] = mapped_column(
        String(42), nullable=False, index=True
    )
    to_address: Mapped[str] = mapped_column(
        String(42), nullable=False, index=True
    )

    # Token info
    token_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # USDT, PLEX, BNB
    token_address: Mapped[str | None] = mapped_column(
        String(42), nullable=True
    )  # null for native BNB

    # Amount
    amount: Mapped[Decimal] = mapped_column(
        DECIMAL(36, 18), nullable=False
    )
    amount_raw: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # raw wei value for precision

    # Direction relative to system wallet
    direction: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # incoming, outgoing, internal

    # Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="confirmed"
    )  # pending, confirmed, failed
    confirmations: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    # Linking to our system entities
    user_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True
    )
    deposit_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    withdrawal_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    # Processing flags
    is_processed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processing_notes: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<BlockchainTxCache(tx_hash={self.tx_hash[:16]}..., "
            f"token={self.token_type}, amount={self.amount}, "
            f"direction={self.direction})>"
        )

    @property
    def is_incoming(self) -> bool:
        """Check if transaction is incoming to system."""
        return self.direction == "incoming"

    @property
    def is_outgoing(self) -> bool:
        """Check if transaction is outgoing from system."""
        return self.direction == "outgoing"
