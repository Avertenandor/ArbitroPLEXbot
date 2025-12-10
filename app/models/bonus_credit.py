"""
BonusCredit model.

Tracks admin-granted bonus credits that participate in ROI calculations.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DECIMAL,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


if TYPE_CHECKING:
    from app.models.admin import Admin
    from app.models.user import User


class BonusCredit(Base):
    """
    BonusCredit entity.

    Tracks admin-granted bonus credits:
    - Acts as a virtual deposit for ROI calculations
    - Has its own ROI cap (typically 500% like regular deposits)
    - Admin can add/remove bonus credits
    - Full audit trail with reason and admin tracking

    Attributes:
        id: Primary key
        user_id: User receiving the bonus
        admin_id: Admin who granted the bonus
        amount: Bonus amount in USDT equivalent
        remaining_amount: Amount still eligible for ROI
        roi_rate: Daily ROI rate (same as level 1 deposits)
        roi_cap_multiplier: Cap multiplier (default 5x = 500%)
        roi_cap_amount: Maximum ROI that can be earned
        roi_paid_amount: Total ROI already paid
        is_active: Whether bonus is still active
        is_roi_completed: Whether ROI cap has been reached
        reason: Admin's reason for granting bonus
        created_at: When bonus was granted
        completed_at: When ROI was fully paid
        cancelled_at: When bonus was cancelled (if applicable)
        cancelled_by: Admin who cancelled (if applicable)
        cancel_reason: Reason for cancellation
    """

    __tablename__ = "bonus_credits"
    __table_args__ = (
        Index("idx_bonus_credits_user_active", "user_id", "is_active"),
        Index("idx_bonus_credits_admin", "admin_id"),
    )

    # Primary key
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    # User reference
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Admin who granted bonus
    admin_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Bonus amount
    amount: Mapped[Decimal] = mapped_column(
        DECIMAL(18, 8),
        nullable=False,
        comment="Original bonus amount in USDT equivalent",
    )

    # ROI tracking (similar to deposits)
    roi_cap_multiplier: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 2),
        default=Decimal("5.00"),
        nullable=False,
        comment="ROI cap multiplier (5.00 = 500%)",
    )
    roi_cap_amount: Mapped[Decimal] = mapped_column(
        DECIMAL(18, 8),
        nullable=False,
        comment="Maximum ROI that can be earned (amount * multiplier)",
    )
    roi_paid_amount: Mapped[Decimal] = mapped_column(
        DECIMAL(18, 8),
        default=Decimal("0"),
        nullable=False,
        comment="Total ROI already paid from this bonus",
    )

    # Next accrual timestamp (like deposits)
    next_accrual_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Next scheduled ROI accrual time",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether bonus is still active for ROI",
    )
    is_roi_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether ROI cap has been reached",
    )

    # Reason and notes
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Admin's reason for granting this bonus",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When ROI cap was reached",
    )

    # Cancellation tracking
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancelled_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
    )
    cancel_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="bonus_credits",
        foreign_keys=[user_id],
    )
    admin: Mapped["Admin | None"] = relationship(
        "Admin",
        foreign_keys=[admin_id],
    )
    canceller: Mapped["Admin | None"] = relationship(
        "Admin",
        foreign_keys=[cancelled_by],
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<BonusCredit(id={self.id}, user_id={self.user_id}, "
            f"amount={self.amount}, active={self.is_active})>"
        )

    @property
    def roi_remaining(self) -> Decimal:
        """Calculate remaining ROI to be paid."""
        return self.roi_cap_amount - self.roi_paid_amount

    @property
    def roi_progress_percent(self) -> float:
        """Calculate ROI progress as percentage."""
        if self.roi_cap_amount <= 0:
            return 0.0
        return float(self.roi_paid_amount / self.roi_cap_amount * 100)
