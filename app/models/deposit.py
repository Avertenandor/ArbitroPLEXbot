"""
Deposit model.

Represents user deposits into the platform.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DECIMAL,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


if TYPE_CHECKING:
    from app.models.deposit_level_version import DepositLevelVersion
    from app.models.plex_payment import PlexPaymentRequirement
    from app.models.user import User


class Deposit(Base):
    """Deposit model - user deposits."""

    __tablename__ = "deposits"
    __table_args__ = (
        CheckConstraint(
            'level >= 1 AND level <= 5',
            name='check_deposit_level_range'
        ),
        CheckConstraint(
            'amount > 0', name='check_deposit_amount_positive'
        ),
        CheckConstraint(
            'roi_cap_amount >= 0',
            name='check_deposit_roi_cap_non_negative'
        ),
        CheckConstraint(
            'roi_paid_amount >= 0',
            name='check_deposit_roi_paid_non_negative'
        ),
        CheckConstraint(
            'roi_paid_amount <= roi_cap_amount',
            name='check_deposit_roi_paid_not_exceeds_cap'
        ),
        Index('idx_deposit_type', 'deposit_type'),
        Index('idx_deposit_usdt_confirmed', 'usdt_confirmed'),
    )

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # User reference
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Deposit details
    level: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )  # 1-5
    amount: Mapped[Decimal] = mapped_column(
        DECIMAL(18, 8), nullable=False
    )

    # New corridor system fields
    deposit_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="level_1"
    )  # test, level_1, level_2, level_3, level_4, level_5
    min_amount: Mapped[Decimal] = mapped_column(
        DECIMAL(18, 8), nullable=False, default=Decimal("0")
    )
    max_amount: Mapped[Decimal] = mapped_column(
        DECIMAL(18, 8), nullable=False, default=Decimal("0")
    )
    usdt_confirmed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    usdt_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    plex_daily_required: Mapped[Decimal] = mapped_column(
        DECIMAL(18, 8), nullable=False, default=Decimal("0")
    )

    # Blockchain data
    tx_hash: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True
    )
    block_number: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    wallet_address: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", index=True
    )  # pending, confirmed, failed, pending_network_recovery (R11-2)

    # R17-1: Deposit version reference
    deposit_version_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("deposit_level_versions.id"), nullable=True, index=True
    )

    # ROI tracking
    roi_cap_amount: Mapped[Decimal] = mapped_column(
        DECIMAL(18, 8), nullable=False, default=Decimal("0")
    )
    roi_paid_amount: Mapped[Decimal] = mapped_column(
        DECIMAL(18, 8), nullable=False, default=Decimal("0")
    )
    is_roi_completed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    # R12-1: Timestamp when ROI was completed
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Next accrual timestamp for individual reward calculation
    next_accrual_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # Consolidation fields
    is_consolidated: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="True if this deposit was created by consolidating multiple transactions"
    )
    consolidated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="When this deposit was consolidated"
    )
    consolidated_tx_hashes: Mapped[list[str] | None] = mapped_column(
        JSONB, nullable=True,
        comment="Original tx hashes if consolidated from multiple transactions"
    )

    # Individual PLEX payment cycle
    plex_cycle_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Start of individual 24h PLEX payment cycle for this deposit"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="deposits",
    )
    deposit_version: Mapped["DepositLevelVersion | None"] = relationship(
        "DepositLevelVersion",
        back_populates="deposits",
    )

    # PLEX payment requirement for this deposit
    plex_payment: Mapped["PlexPaymentRequirement | None"] = relationship(
        "PlexPaymentRequirement",
        back_populates="deposit",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<Deposit(id={self.id}, user_id={self.user_id}, "
            f"level={self.level}, amount={self.amount}, status={self.status})>"
        )

    @property
    def level_name(self) -> str:
        """Human-readable level name."""
        level_names = {
            "test": "Тестовый депозит",
            "level_1": "Уровень 1",
            "level_2": "Уровень 2",
            "level_3": "Уровень 3",
            "level_4": "Уровень 4",
            "level_5": "Уровень 5",
        }
        return level_names.get(self.deposit_type, f"Уровень {self.level}")

    @property
    def is_test_deposit(self) -> bool:
        """Check if this is a test deposit."""
        return self.deposit_type == "test"

    @property
    def plex_status_text(self) -> str:
        """Get PLEX payment status as text."""
        if not self.plex_payment:
            return "Нет данных"

        if self.plex_payment.is_paid:
            return "Оплачен"
        elif self.plex_payment.is_overdue:
            return "Просрочен"
        elif self.plex_payment.payment_due_at:
            return "Ожидает оплаты"
        return "Не требуется"
