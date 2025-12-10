"""
Blockchain Sync State model.

Tracks the synchronization state of blockchain scanning.
"""

from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BlockchainSyncState(Base):
    """
    Tracks blockchain synchronization state.
    
    Used to:
    - Know which blocks have been synced
    - Resume sync after restart
    - Track sync progress for different tokens
    """

    __tablename__ = "blockchain_sync_state"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Token/chain identification
    token_type: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True, index=True
    )  # USDT, PLEX, BNB

    # Sync range
    first_synced_block: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    last_synced_block: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, index=True
    )

    # Statistics
    total_transactions: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    incoming_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    outgoing_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    # Full sync status
    full_sync_completed: Mapped[bool] = mapped_column(
        default=False, nullable=False
    )
    full_sync_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    full_sync_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Error tracking
    last_error: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    error_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
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
