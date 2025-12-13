"""
UserInquiry model.

Represents user inquiries/questions to admins.
This is separate from technical support - for general questions and help.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


if TYPE_CHECKING:
    from app.models.admin import Admin
    from app.models.user import User


class InquiryStatus(StrEnum):
    """Inquiry status enumeration."""

    NEW = "new"  # Новое обращение, ждет ответа
    IN_PROGRESS = "in_progress"  # Админ взял в работу
    CLOSED = "closed"  # Закрыто


class UserInquiry(Base):
    """
    UserInquiry entity.

    Represents a user inquiry/question to admins:
    - User asks a question via "Задать вопрос" button
    - Admin picks it up and starts dialog
    - Dialog continues until closed

    Attributes:
        id: Primary key
        user_id: User who created inquiry
        telegram_id: User's telegram ID (for notifications)
        initial_question: The original question text
        status: Current status (new/in_progress/closed)
        assigned_admin_id: Admin who took the inquiry
        created_at: When inquiry was created
        assigned_at: When admin took the inquiry
        closed_at: When inquiry was closed
        closed_by: Who closed (user/admin)
    """

    __tablename__ = "user_inquiries"

    # Primary key
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    # User who created inquiry
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )

    # Telegram ID for sending notifications
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )

    # Initial question text
    initial_question: Mapped[str] = mapped_column(
        Text, nullable=False
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=InquiryStatus.NEW.value,
        index=True,
    )

    # Admin assignment
    assigned_admin_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("admins.id"), nullable=True, index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )
    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_by: Mapped[str | None] = mapped_column(
        String(20), nullable=True  # "user" or "admin"
    )

    # Relationships
    user: Mapped["User"] = relationship("User", lazy="joined")
    assigned_admin: Mapped[Optional["Admin"]] = relationship(
        "Admin", lazy="joined"
    )
    messages: Mapped[list["InquiryMessage"]] = relationship(
        "InquiryMessage",
        back_populates="inquiry",
        lazy="selectin",
        order_by="InquiryMessage.created_at",
    )

    def __repr__(self) -> str:
        return (
            f"<UserInquiry(id={self.id}, user_id={self.user_id}, "
            f"status={self.status})>"
        )


class InquiryMessage(Base):
    """
    InquiryMessage entity.

    Represents a message in an inquiry dialog.

    Attributes:
        id: Primary key
        inquiry_id: Parent inquiry
        sender_type: Who sent the message (user/admin)
        sender_id: ID of sender (user_id or admin_id)
        message_text: Message content
        created_at: When message was sent
    """

    __tablename__ = "inquiry_messages"

    # Primary key
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    # Parent inquiry
    inquiry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_inquiries.id"), nullable=False, index=True
    )

    # Sender info
    sender_type: Mapped[str] = mapped_column(
        String(20), nullable=False  # "user" or "admin"
    )
    sender_id: Mapped[int] = mapped_column(
        Integer, nullable=False
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

    # Relationship
    inquiry: Mapped["UserInquiry"] = relationship(
        "UserInquiry", back_populates="messages"
    )

    def __repr__(self) -> str:
        return (
            f"<InquiryMessage(id={self.id}, inquiry_id={self.inquiry_id}, "
            f"sender_type={self.sender_type})>"
        )
