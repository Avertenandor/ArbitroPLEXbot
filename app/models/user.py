"""
User model.

Represents a registered Telegram user in the system.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

import bcrypt
from sqlalchemy import (
    DECIMAL,
    BigInteger,
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
    from app.models.bonus_credit import BonusCredit
    from app.models.deposit import Deposit
    from app.models.plex_payment import PlexPaymentRequirement
    from app.models.transaction import Transaction
    from app.models.user_fsm_state import UserFsmState
    from app.models.user_notification_settings import UserNotificationSettings


class User(Base):
    """User model - registered Telegram users."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            'balance >= 0', name='check_user_balance_non_negative'
        ),
        CheckConstraint(
            'total_earned >= 0',
            name='check_user_total_earned_non_negative'
        ),
        CheckConstraint(
            'pending_earnings >= 0',
            name='check_user_pending_earnings_non_negative'
        ),
    )

    # Primary key
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    # Telegram data
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    username: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    referral_code: Mapped[str | None] = mapped_column(
        String(20), nullable=True, unique=True, index=True
    )

    # Wallet and financial
    wallet_address: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )
    financial_password: Mapped[str] = mapped_column(
        String(255), nullable=False
    )

    # Optional contacts (from TZ)
    phone: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    email: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    # Balances
    balance: Mapped[Decimal] = mapped_column(
        DECIMAL(18, 8), default=Decimal("0"), nullable=False
    )
    total_earned: Mapped[Decimal] = mapped_column(
        DECIMAL(18, 8), default=Decimal("0"), nullable=False
    )
    pending_earnings: Mapped[Decimal] = mapped_column(
        DECIMAL(18, 8), default=Decimal("0"), nullable=False
    )

    # Bonus balance (admin-granted, participates in ROI calculations)
    bonus_balance: Mapped[Decimal] = mapped_column(
        DECIMAL(18, 8),
        default=Decimal("0"),
        nullable=False,
        comment="Admin-granted bonus balance for ROI calculations",
    )
    bonus_roi_earned: Mapped[Decimal] = mapped_column(
        DECIMAL(18, 8),
        default=Decimal("0"),
        nullable=False,
        comment="Total ROI earned from bonus credits",
    )

    # Referral
    referrer_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Status flags
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    is_banned: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    earnings_blocked: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    suspicious: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    withdrawal_blocked: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    # R8-2: Bot blocked tracking
    bot_blocked: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    bot_blocked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # R13-3: Language preference
    language: Mapped[str | None] = mapped_column(
        String(10), nullable=True, default="ru", index=True
    )

    # Rate limiting for financial password
    finpass_attempts: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    finpass_locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Deposit tracking (auto-detection from blockchain)
    total_deposited_usdt: Mapped[Decimal] = mapped_column(
        DECIMAL(18, 8),
        default=Decimal("0"),
        nullable=False,
        comment="Total USDT deposited to system wallet from user wallet"
    )
    is_active_depositor: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="True if total_deposited_usdt >= 30 USDT"
    )
    last_deposit_scan_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time deposits were scanned from blockchain"
    )
    deposit_tx_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of deposit transactions found"
    )

    # Work status tracking
    work_status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        nullable=False,
        index=True,
        comment="Work status: active, suspended_no_plex, suspended_no_payment"
    )
    last_plex_check_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time PLEX balance was checked"
    )
    last_plex_balance: Mapped[Decimal | None] = mapped_column(
        DECIMAL(18, 8),
        nullable=True,
        comment="Last checked PLEX balance on wallet"
    )
    plex_insufficient_since: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When PLEX balance first dropped below minimum"
    )
    deposits_consolidated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if pre-existing deposits were consolidated"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False
    )
    last_active: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    referrer: Mapped[Optional["User"]] = relationship(
        "User",
        remote_side=[id],
        back_populates="referrals",
        foreign_keys=[referrer_id],
    )
    referrals: Mapped[list["User"]] = relationship(
        "User",
        back_populates="referrer",
        foreign_keys=[referrer_id]
    )

    # Deposits relationship
    deposits: Mapped[list["Deposit"]] = relationship(
        "Deposit",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # Transactions relationship
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # Notification settings relationship
    notification_settings: Mapped["UserNotificationSettings | None"] = relationship(
        "UserNotificationSettings",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # R11-2: FSM states relationship (fallback when Redis is unavailable)
    fsm_states: Mapped[list["UserFsmState"]] = relationship(
        "UserFsmState",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # PLEX payment requirements for deposits
    plex_payments: Mapped[list["PlexPaymentRequirement"]] = relationship(
        "PlexPaymentRequirement",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # Bonus credits relationship
    bonus_credits: Mapped[list["BonusCredit"]] = relationship(
        "BonusCredit",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="BonusCredit.user_id",
    )

    @property
    def masked_wallet(self) -> str:
        """
        Get masked wallet address for display.

        Returns:
            Masked wallet address (first 10 + ... + last 8)
        """
        if len(self.wallet_address) > 20:
            return f"{self.wallet_address[:10]}...{self.wallet_address[-8:]}"
        return self.wallet_address

    @property
    def required_daily_plex(self) -> Decimal:
        """
        Calculate required daily PLEX based on deposit amount.

        Formula: deposit_amount * 10 PLEX per dollar per day.

        Returns:
            Required PLEX amount per day
        """
        return self.total_deposited_usdt * Decimal("10")

    @property
    def deposit_status_text(self) -> str:
        """
        Get human-readable deposit status.

        Returns:
            Status text for display
        """
        if not self.is_active_depositor:
            return "❌ Неактивен (< 30 USDT)"
        return f"✅ Активен ({self.total_deposited_usdt:.2f} USDT)"

    def set_financial_password(self, password: str) -> None:
        """
        Set financial password with bcrypt hashing.

        Args:
            password: Plain text password to hash and store
        """
        self.financial_password = bcrypt.hashpw(
            password.encode(), bcrypt.gensalt()
        ).decode()

    def verify_financial_password(self, password: str) -> bool:
        """
        Verify financial password against stored hash.

        Args:
            password: Plain text password to verify

        Returns:
            True if password matches, False otherwise
        """
        if not self.financial_password:
            return False
        return bcrypt.checkpw(
            password.encode(), self.financial_password.encode()
        )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<User(id={self.id}, telegram_id={self.telegram_id}, "
            f"username={self.username})>"
        )
