"""
PLEX Payment Requirement model.

Tracks daily PLEX payments required for each deposit.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DECIMAL,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.deposit import Deposit
    from app.models.user import User


class PlexPaymentStatus:
    """PLEX payment status constants."""

    ACTIVE = "active"           # Normal state, waiting for payment
    WARNING_SENT = "warning"    # Warning sent after 25h without payment
    BLOCKED = "blocked"         # Blocked after 49h without payment
    PAID = "paid"               # Payment confirmed for current day


class PlexPaymentRequirement(Base):
    """
    PLEX payment requirement for deposits.

    Tracks the daily PLEX payment obligation for each deposit.
    Timeline from deposit creation:
    - 0h: Deposit created, next_payment_due = created_at + 24h
    - 24h: Payment due
    - 25h: Warning sent if no payment (warning_due)
    - 49h: Block deposit if still no payment (block_due)
    """

    __tablename__ = "plex_payment_requirements"
    __table_args__ = (
        CheckConstraint(
            "daily_plex_required > 0",
            name="check_plex_daily_required_positive"
        ),
    )

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # User reference
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Deposit reference
    deposit_id: Mapped[int] = mapped_column(
        ForeignKey("deposits.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Requirements
    daily_plex_required: Mapped[Decimal] = mapped_column(
        DECIMAL(18, 8),
        nullable=False,
        comment="Daily PLEX payment required (deposit_amount * 10)"
    )

    # Deadlines (calculated from deposit creation)
    next_payment_due: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Next payment due (deposit_created_at + 24h)"
    )

    warning_due: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Warning will be sent at this time (deposit_created_at + 25h)"
    )

    block_due: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Block at this time if not paid (deposit_created_at + 49h)"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PlexPaymentStatus.ACTIVE,
        index=True,
        comment="active, warning, blocked, paid"
    )

    # Payment tracking
    last_payment_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful PLEX payment timestamp"
    )

    last_payment_tx_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Last payment transaction hash"
    )

    total_paid_plex: Mapped[Decimal] = mapped_column(
        DECIMAL(18, 8),
        nullable=False,
        default=Decimal("0"),
        comment="Total PLEX paid for this deposit"
    )

    days_paid: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of days paid for this deposit"
    )

    # Warning tracking
    warning_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When warning was sent"
    )

    warning_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of warnings sent"
    )

    # Work activation tracking (pay first, work after)
    is_work_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True if PLEX payment received, deposit can work"
    )

    first_payment_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When first PLEX payment was received (starts work)"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
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
        back_populates="plex_payments",
        lazy="selectin"
    )

    deposit: Mapped["Deposit"] = relationship(
        "Deposit",
        back_populates="plex_payment",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<PlexPaymentRequirement("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"deposit_id={self.deposit_id}, "
            f"daily_plex={self.daily_plex_required}, "
            f"status={self.status}"
            f")>"
        )

    @staticmethod
    def calculate_deadlines(
        deposit_created_at: datetime
    ) -> tuple[datetime, datetime, datetime]:
        """
        Calculate payment deadlines from deposit creation time.

        Args:
            deposit_created_at: Deposit creation timestamp

        Returns:
            Tuple of (next_payment_due, warning_due, block_due)
        """
        next_payment_due = deposit_created_at + timedelta(hours=24)
        warning_due = deposit_created_at + timedelta(hours=25)
        block_due = deposit_created_at + timedelta(hours=49)
        return next_payment_due, warning_due, block_due

    def is_payment_overdue(self) -> bool:
        """Check if payment is overdue."""
        return datetime.now(UTC) > self.next_payment_due

    def is_warning_due(self) -> bool:
        """Check if warning should be sent."""
        return (
            datetime.now(UTC) > self.warning_due
            and self.status == PlexPaymentStatus.ACTIVE
        )

    def is_block_due(self) -> bool:
        """Check if deposit should be blocked."""
        return (
            datetime.now(UTC) > self.block_due
            and self.status in (PlexPaymentStatus.ACTIVE, PlexPaymentStatus.WARNING_SENT)
        )

    def mark_paid(self, tx_hash: str, amount: Decimal) -> None:
        """
        Mark payment as received and update deadlines.

        Args:
            tx_hash: Transaction hash
            amount: Amount paid
        """
        now = datetime.now(UTC)
        self.last_payment_at = now
        self.last_payment_tx_hash = tx_hash
        self.total_paid_plex += amount
        self.days_paid += 1
        self.status = PlexPaymentStatus.PAID

        # Activate work on first payment (pay first, work after)
        if not self.is_work_active:
            self.is_work_active = True
            self.first_payment_at = now

        # Reset deadlines for next day (individual 24h cycle)
        self.next_payment_due = now + timedelta(hours=24)
        self.warning_due = now + timedelta(hours=25)
        self.block_due = now + timedelta(hours=49)

    def mark_warning_sent(self) -> None:
        """Mark warning as sent."""
        self.warning_sent_at = datetime.now(UTC)
        self.warning_count += 1
        self.status = PlexPaymentStatus.WARNING_SENT

    def mark_blocked(self) -> None:
        """Mark deposit as blocked due to non-payment."""
        self.status = PlexPaymentStatus.BLOCKED
