"""
SponsorInquiry model.

Represents referral-to-sponsor communication.
Allows referrals to ask questions directly to their sponsor (referrer).
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


if TYPE_CHECKING:
    from app.models.user import User


class SponsorInquiryStatus(StrEnum):
    """Sponsor inquiry status enumeration."""

    NEW = "new"  # Новое, спонсор ещё не видел
    IN_PROGRESS = "in_progress"  # Спонсор читает/отвечает
    CLOSED = "closed"  # Диалог закрыт


class SponsorInquiry(Base):
    """
    SponsorInquiry entity.

    Represents a referral's question to their direct sponsor:
    - Referral asks a question via "💬 Написать спонсору"
    - Sponsor receives notification and can reply
    - Dialog continues until closed by either party

    Attributes:
        id: Primary key
        referral_id: User who asks the question (referral)
        referral_telegram_id: Referral's telegram ID (for notifications)
        sponsor_id: User who receives the question (sponsor/referrer)
        sponsor_telegram_id: Sponsor's telegram ID (for notifications)
        initial_question: The original question text
        status: Current status (new/in_progress/closed)
        created_at: When inquiry was created
        last_message_at: When last message was sent
        closed_at: When inquiry was closed
        closed_by: Who closed ('referral' or 'sponsor')
        is_read_by_sponsor: Whether sponsor has seen the inquiry
        is_read_by_referral: Whether referral has seen the last response
    """

    __tablename__ = "sponsor_inquiries"

    # Primary key
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    # Referral (who asks)
    referral_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    referral_telegram_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )

    # Sponsor (who answers)
    sponsor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    sponsor_telegram_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )

    # Initial question
    initial_question: Mapped[str] = mapped_column(
        Text, nullable=False
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SponsorInquiryStatus.NEW.value,
        index=True,
    )

    # Read status
    is_read_by_sponsor: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    is_read_by_referral: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False  # Referral already knows their question
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_by: Mapped[str | None] = mapped_column(
        String(20), nullable=True  # 'referral' or 'sponsor'
    )

    # Relationships
    referral: Mapped["User"] = relationship(
        "User",
        foreign_keys=[referral_id],
        backref="sponsor_inquiries_sent",
    )
    sponsor: Mapped["User"] = relationship(
        "User",
        foreign_keys=[sponsor_id],
        backref="sponsor_inquiries_received",
    )
    messages: Mapped[list["SponsorInquiryMessage"]] = relationship(
        "SponsorInquiryMessage",
        back_populates="inquiry",
        order_by="SponsorInquiryMessage.created_at",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<SponsorInquiry(id={self.id}, "
            f"referral_id={self.referral_id}, "
            f"sponsor_id={self.sponsor_id}, "
            f"status={self.status})>"
        )


class SponsorInquiryMessage(Base):
    """
    Message in sponsor inquiry dialog.

    Stores individual messages between referral and sponsor.
    """

    __tablename__ = "sponsor_inquiry_messages"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    inquiry_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sponsor_inquiries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Who sent: 'referral' or 'sponsor'
    sender_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )

    # Message content
    message_text: Mapped[str] = mapped_column(
        Text, nullable=False
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    # Is read by recipient
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Relationship back to inquiry
    inquiry: Mapped["SponsorInquiry"] = relationship(
        "SponsorInquiry",
        back_populates="messages",
    )

    def __repr__(self) -> str:
        return (
            f"<SponsorInquiryMessage(id={self.id}, "
            f"inquiry_id={self.inquiry_id}, "
            f"sender={self.sender_type})>"
        )
