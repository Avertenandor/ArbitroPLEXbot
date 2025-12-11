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
    """PLEX payment status constants.

    NOTE: Some services use legacy aliases WARNING_SENT/PAID.
    To keep backward compatibility we map them to actual values.
    """

    PENDING = "pending"  # Ожидает первого платежа
    ACTIVE = "active"  # Активен, платежи регулярные
    WARNING = "warning"  # Предупреждение (25+ часов)
    OVERDUE = "overdue"  # Просрочен (49+ часов)
    BLOCKED = "blocked"  # Заблокирован

    # Backward-compatible aliases used in older code paths
    WARNING_SENT = WARNING  # same as "warning"
    PAID = ACTIVE  # treated as active/оплачен


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
    __table_args__ = (CheckConstraint("daily_plex_required > 0", name="check_plex_daily_required_positive"),)

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # User reference
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Deposit reference
    deposit_id: Mapped[int] = mapped_column(
        ForeignKey("deposits.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    # Requirements
    daily_plex_required: Mapped[Decimal] = mapped_column(
        DECIMAL(18, 8), nullable=False, comment="Daily PLEX payment required (deposit_amount * 10)"
    )

    # Deadlines (calculated from deposit creation)
    next_payment_due: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True, comment="Next payment due (deposit_created_at + 24h)"
    )

    warning_due: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="Warning will be sent at this time (deposit_created_at + 25h)"
    )

    block_due: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="Block at this time if not paid (deposit_created_at + 49h)"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PlexPaymentStatus.PENDING,
        index=True,
        comment="pending, active, warning, overdue, blocked",
    )

    # Payment tracking
    last_payment_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Last successful PLEX payment timestamp"
    )

    last_payment_tx_hash: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Last payment transaction hash"
    )

    last_check_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Когда последний раз проверяли платёж"
    )

    total_plex_paid: Mapped[Decimal] = mapped_column(
        DECIMAL(18, 8), nullable=False, default=Decimal("0"), comment="Всего PLEX оплачено за всё время"
    )

    days_paid: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Number of days paid for this deposit"
    )

    consecutive_days_paid: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Сколько дней подряд оплачено"
    )

    # Warning tracking
    warning_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When warning was sent"
    )

    warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Number of warnings sent")

    # Work activation tracking (pay first, work after)
    is_work_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="True if PLEX payment received, deposit can work"
    )

    first_payment_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When first PLEX payment was received (starts work)"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="plex_payments", lazy="selectin")

    deposit: Mapped["Deposit"] = relationship("Deposit", back_populates="plex_payment", lazy="selectin")

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
    def calculate_daily_requirement(deposit_amount: Decimal) -> Decimal:
        """
        Рассчитать ежедневное требование PLEX.

        Args:
            deposit_amount: Сумма депозита

        Returns:
            Ежедневное требование PLEX (deposit_amount * 10)
        """
        return deposit_amount * Decimal("10")

    @staticmethod
    def calculate_deadlines(deposit_created_at: datetime) -> tuple[datetime, datetime, datetime]:
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

    def is_payment_due(self) -> bool:
        """
        Проверить, нужна ли оплата сегодня.

        Returns:
            True если оплата нужна
        """
        now = datetime.now(UTC)
        return now >= self.next_payment_due

    def get_next_payment_deadline(self) -> datetime:
        """
        Получить крайний срок следующего платежа.

        Returns:
            Datetime следующего крайнего срока
        """
        return self.next_payment_due

    def get_payment_status_text(self) -> str:
        """
        Получить текстовое описание статуса платежа.

        Returns:
            Текстовое описание статуса
        """
        now = datetime.now(UTC)
        hours_since_due = (now - self.next_payment_due).total_seconds() / 3600

        if self.status == PlexPaymentStatus.PENDING:
            return "⏳ Ожидает первого платежа"
        elif self.status == PlexPaymentStatus.ACTIVE:
            if hours_since_due < 0:
                hours_left = abs(hours_since_due)
                return f"✅ Активен (платёж через {hours_left:.1f}ч)"
            elif hours_since_due < 1:
                return "⏰ Платёж ожидается (до 1 часа)"
            else:
                return f"⏰ Ожидание платежа ({hours_since_due:.1f}ч)"
        elif self.status == PlexPaymentStatus.WARNING:
            return f"⚠️ Предупреждение (просрочка {hours_since_due:.1f}ч)"
        elif self.status == PlexPaymentStatus.OVERDUE:
            return f"❌ Просрочен (просрочка {hours_since_due:.1f}ч)"
        elif self.status == PlexPaymentStatus.BLOCKED:
            return "🚫 Заблокирован"
        else:
            return f"❓ Неизвестный статус: {self.status}"

    def mark_paid(self, tx_hash: str, amount: Decimal) -> None:
        """Register a PLEX payment for this requirement.

        Supports paying for multiple days at once: amount can be
        more than daily_plex_required. All payments go into
        total_plex_paid; due dates are shifted by 24h from now
        so that next check happens in следующие сутки.
        """
        now = datetime.now(UTC)
        self.last_payment_at = now
        self.last_payment_tx_hash = tx_hash
        self.last_check_at = now
        self.total_plex_paid += amount
        # Approximate how many full days covered by total_paid
        try:
            full_days = int(self.total_plex_paid / self.daily_plex_required)
        except Exception:  # pragma: no cover - defensive
            full_days = self.days_paid

        if full_days < 0:
            full_days = 0

        self.days_paid = full_days
        self.consecutive_days_paid += 1
        self.status = PlexPaymentStatus.ACTIVE

        # Activate work on first payment (pay first, work after)
        if not self.is_work_active:
            self.is_work_active = True
            self.first_payment_at = now

        # Reset deadlines for next day (individual 24h cycle)
        self.next_payment_due = now + timedelta(hours=24)
        self.warning_due = now + timedelta(hours=25)
        self.block_due = now + timedelta(hours=49)

    def mark_daily_paid(self, tx_hash: str, amount: Decimal) -> None:
        """Backward-compatible wrapper for single-day payment.

        Older code calls mark_daily_paid; internally we route to
        mark_paid so that общая логика учёта не дублируется.
        """
        self.mark_paid(tx_hash=tx_hash, amount=amount)

    def is_payment_overdue(self) -> bool:
        """Check if payment is overdue."""
        return datetime.now(UTC) > self.next_payment_due

    def is_warning_due(self) -> bool:
        """
        Проверить, нужно ли отправить предупреждение.

        Returns:
            True если прошло 25+ часов без оплаты
        """
        now = datetime.now(UTC)
        return now >= self.warning_due and self.status in (PlexPaymentStatus.PENDING, PlexPaymentStatus.ACTIVE)

    def is_block_due(self) -> bool:
        """
        Проверить, нужно ли заблокировать депозит.

        Returns:
            True если прошло 49+ часов без оплаты
        """
        now = datetime.now(UTC)
        return now >= self.block_due and self.status != PlexPaymentStatus.BLOCKED

    def mark_warning_sent(self) -> None:
        """Отметить отправку предупреждения."""
        self.warning_sent_at = datetime.now(UTC)
        self.warning_count += 1
        self.status = PlexPaymentStatus.WARNING
        self.consecutive_days_paid = 0  # Сбросить последовательность

    def mark_overdue(self) -> None:
        """Отметить депозит как просроченный."""
        self.status = PlexPaymentStatus.OVERDUE
        self.consecutive_days_paid = 0  # Сбросить последовательность

    def mark_blocked(self) -> None:
        """Отметить депозит как заблокированный."""
        self.status = PlexPaymentStatus.BLOCKED
        self.consecutive_days_paid = 0  # Сбросить последовательность
