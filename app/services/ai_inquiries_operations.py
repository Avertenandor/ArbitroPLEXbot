"""
AI Inquiries Operations.

Business logic operations for inquiries modification.
Handles inquiry state changes and message creation.
"""
from datetime import UTC, datetime
from typing import Any
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user_inquiry import InquiryMessage, InquiryStatus, UserInquiry


async def assign_inquiry_to_admin(
    session: AsyncSession,
    inquiry: UserInquiry,
    admin: Any,
) -> None:
    """
    Assign inquiry to admin and update status.

    Args:
        session: Database session
        inquiry: UserInquiry object
        admin: Admin object
    """
    inquiry.status = InquiryStatus.IN_PROGRESS
    inquiry.assigned_admin_id = admin.id
    inquiry.assigned_at = datetime.now(UTC)
    await session.commit()


async def auto_assign_if_needed(
    session: AsyncSession,
    inquiry: UserInquiry,
    admin: Any,
) -> None:
    """
    Auto-assign inquiry to admin if not assigned.

    Args:
        session: Database session
        inquiry: UserInquiry object
        admin: Admin object
    """
    if not inquiry.assigned_admin_id:
        inquiry.status = InquiryStatus.IN_PROGRESS
        inquiry.assigned_admin_id = admin.id
        inquiry.assigned_at = datetime.now(UTC)


async def create_admin_message(
    session: AsyncSession,
    inquiry_id: int,
    admin: Any,
    message_text: str,
) -> InquiryMessage:
    """
    Create admin message record.

    Args:
        session: Database session
        inquiry_id: Inquiry ID
        admin: Admin object
        message_text: Message text

    Returns:
        Created InquiryMessage object
    """
    new_message = InquiryMessage(
        inquiry_id=inquiry_id,
        sender_type="admin",
        sender_id=admin.id,
        message_text=f"[АРЬЯ] {message_text}",
        created_at=datetime.now(UTC),
    )
    session.add(new_message)
    return new_message


async def send_message_to_user(
    bot: Any,
    telegram_id: int,
    formatted_message: str,
) -> tuple[bool, str | None]:
    """
    Send message to user via Telegram bot.

    Args:
        bot: Bot instance
        telegram_id: User's telegram ID
        formatted_message: Formatted message text

    Returns:
        Tuple of (success, error_message)
    """
    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=formatted_message,
            parse_mode="Markdown",
        )
        return True, None
    except Exception as e:
        error_msg = f"Failed to send message: {e}"
        logger.error(error_msg)
        return False, f"❌ Не удалось отправить: {str(e)}"


async def close_inquiry_with_reason(
    session: AsyncSession,
    inquiry: UserInquiry,
    admin: Any,
    reason: str | None = None,
) -> None:
    """
    Close inquiry and optionally add closing message.

    Args:
        session: Database session
        inquiry: UserInquiry object
        admin: Admin object
        reason: Optional closing reason
    """
    inquiry.status = InquiryStatus.CLOSED
    inquiry.closed_at = datetime.now(UTC)
    inquiry.closed_by = "admin"

    if reason:
        new_message = InquiryMessage(
            inquiry_id=inquiry.id,
            sender_type="admin",
            sender_id=admin.id,
            message_text=f"[АРЬЯ] Обращение закрыто: {reason}",
            created_at=datetime.now(UTC),
        )
        session.add(new_message)

    await session.commit()


def log_inquiry_action(
    action: str,
    admin_telegram_id: int,
    inquiry_id: int,
    details: str = "",
) -> None:
    """
    Log inquiry action.

    Args:
        action: Action name (took, replied, closed)
        admin_telegram_id: Admin's telegram ID
        inquiry_id: Inquiry ID
        details: Additional details
    """
    log_msg = (
        f"AI INQUIRIES: Admin {admin_telegram_id} "
        f"{action} inquiry {inquiry_id}"
    )
    if details:
        log_msg += f": {details}"
    logger.info(log_msg)
