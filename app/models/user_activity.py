"""
User Activity Model.

Tracks ALL user actions in the system for comprehensive analytics:
- Bot interactions (start, menu clicks, messages)
- Registration events (wallet setup, verification)
- Financial events (deposits, withdrawals, PLEX payments)
- Support interactions
- Any other loggable action
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


if TYPE_CHECKING:
    from app.models.user import User


class ActivityType:
    """Activity type constants."""

    # Bot lifecycle
    START = "start"                     # User pressed /start
    START_REFERRAL = "start_referral"   # Started with referral link
    MENU_OPEN = "menu_open"             # Opened main menu

    # Registration flow
    WALLET_ENTERED = "wallet_entered"   # User entered wallet address
    WALLET_VERIFIED = "wallet_verified"  # Wallet verified on blockchain
    PLEX_PAID = "plex_paid"             # Paid 10 PLEX for entry
    FINPASS_SET = "finpass_set"         # Set financial password

    # Financial actions
    DEPOSIT_STARTED = "deposit_started"     # Started deposit flow
    DEPOSIT_CONFIRMED = "deposit_confirmed"  # Deposit confirmed
    WITHDRAWAL_REQUESTED = "withdrawal_requested"
    WITHDRAWAL_COMPLETED = "withdrawal_completed"
    PLEX_DAILY_PAID = "plex_daily_paid"     # Daily PLEX payment

    # User interactions
    MESSAGE_SENT = "message_sent"       # Any message to bot
    BUTTON_CLICKED = "button_clicked"   # Button/callback interaction
    SUPPORT_REQUEST = "support_request"  # Opened support ticket
    INQUIRY_SENT = "inquiry_sent"       # Sent inquiry to admins

    # Profile actions
    PROFILE_VIEW = "profile_view"
    BALANCE_VIEW = "balance_view"
    REFERRAL_LINK_VIEW = "referral_link_view"
    REFERRAL_LINK_SHARED = "referral_link_shared"

    # AI interactions
    AI_QUESTION = "ai_question"         # Asked AI assistant
    AI_RESPONSE = "ai_response"         # Received AI response

    # Errors
    ERROR_OCCURRED = "error_occurred"   # User encountered error

    # Admin actions on user
    ADMIN_BONUS = "admin_bonus"         # Admin granted bonus
    ADMIN_BAN = "admin_ban"             # Admin banned user
    ADMIN_UNBAN = "admin_unban"         # Admin unbanned user


class UserActivity(Base):
    """
    User activity log entry.

    Stores every trackable action with full context.
    """

    __tablename__ = "user_activities"
    __table_args__ = (
        # Index for fast user activity lookup
        Index("ix_user_activities_user_id_created", "user_id", "created_at"),
        # Index for activity type filtering
        Index("ix_user_activities_type_created", "activity_type", "created_at"),
        # Index for date-based analytics
        Index("ix_user_activities_created_at", "created_at"),
    )

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # User reference (nullable for anonymous actions like failed starts)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Telegram ID (for tracking before user is created)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # Activity type
    activity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    # Activity description (human-readable)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Full message text (for messages)
    message_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Additional data as JSON (flexible storage)
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    user: Mapped["User | None"] = relationship(
        "User",
        back_populates="activities",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<UserActivity(id={self.id}, user_id={self.user_id}, "
            f"type={self.activity_type}, created={self.created_at})>"
        )

    @property
    def type_emoji(self) -> str:
        """Get emoji for activity type."""
        emoji_map = {
            ActivityType.START: "🚀",
            ActivityType.START_REFERRAL: "🔗",
            ActivityType.WALLET_ENTERED: "💳",
            ActivityType.WALLET_VERIFIED: "✅",
            ActivityType.PLEX_PAID: "💰",
            ActivityType.DEPOSIT_STARTED: "📥",
            ActivityType.DEPOSIT_CONFIRMED: "✅",
            ActivityType.WITHDRAWAL_REQUESTED: "📤",
            ActivityType.WITHDRAWAL_COMPLETED: "💸",
            ActivityType.MESSAGE_SENT: "💬",
            ActivityType.BUTTON_CLICKED: "🔘",
            ActivityType.SUPPORT_REQUEST: "🆘",
            ActivityType.AI_QUESTION: "🤖",
            ActivityType.ERROR_OCCURRED: "❌",
            ActivityType.ADMIN_BONUS: "🎁",
        }
        return emoji_map.get(self.activity_type, "📝")
