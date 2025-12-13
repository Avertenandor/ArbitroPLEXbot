"""
AI Inquiries Repository.

Database access layer for user inquiries.
Provides data access methods for inquiries and messages.
"""
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.models.user_inquiry import InquiryStatus, UserInquiry


async def get_inquiries_with_filter(
    session: AsyncSession,
    status: str | None = None,
    limit: int = 20,
) -> list[UserInquiry]:
    """
    Get inquiries list with optional status filter.

    Args:
        session: Database session
        status: Optional status filter
        limit: Maximum number of results

    Returns:
        List of UserInquiry objects
    """
    stmt = (
        select(UserInquiry)
        .options(joinedload(UserInquiry.user))
        .options(joinedload(UserInquiry.assigned_admin))
        .order_by(UserInquiry.created_at.desc())
        .limit(limit)
    )

    if status:
        stmt = stmt.where(UserInquiry.status == status.lower())

    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


async def get_inquiry_by_id(
    session: AsyncSession,
    inquiry_id: int,
    with_messages: bool = False,
) -> UserInquiry | None:
    """
    Get inquiry by ID with relationships.

    Args:
        session: Database session
        inquiry_id: Inquiry ID
        with_messages: Include messages if True

    Returns:
        UserInquiry object or None
    """
    stmt = (
        select(UserInquiry)
        .options(joinedload(UserInquiry.user))
        .options(joinedload(UserInquiry.assigned_admin))
        .where(UserInquiry.id == inquiry_id)
    )

    if with_messages:
        stmt = stmt.options(joinedload(UserInquiry.messages))

    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_inquiries_counts(
    session: AsyncSession,
) -> dict[str, int]:
    """
    Get count of inquiries by status.

    Args:
        session: Database session

    Returns:
        Dict with status counts
    """
    count_stmt = (
        select(UserInquiry.status, func.count(UserInquiry.id))
        .group_by(UserInquiry.status)
    )
    count_result = await session.execute(count_stmt)
    counts = {row[0]: row[1] for row in count_result.all()}

    return {
        "new": counts.get("new", 0),
        "in_progress": counts.get("in_progress", 0),
        "closed": counts.get("closed", 0),
    }


def validate_status(status: str | None) -> tuple[bool, str | None]:
    """
    Validate inquiry status value.

    Args:
        status: Status string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not status:
        return True, None

    valid_statuses = ["new", "in_progress", "closed"]
    if status.lower() not in valid_statuses:
        error_msg = (
            f"❌ Неверный статус. "
            f"Допустимые: {', '.join(valid_statuses)}"
        )
        return False, error_msg

    return True, None


def validate_message(message: str | None) -> tuple[bool, str | None]:
    """
    Validate message text.

    Args:
        message: Message text to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not message or len(message) < 3:
        return (
            False,
            "❌ Сообщение слишком короткое (мин. 3 символа)"
        )
    return True, None


def validate_inquiry_status(
    inquiry: UserInquiry | None,
    inquiry_id: int,
    allow_closed: bool = False,
) -> tuple[bool, str | None]:
    """
    Validate inquiry exists and check status.

    Args:
        inquiry: UserInquiry object or None
        inquiry_id: Inquiry ID for error message
        allow_closed: Allow closed inquiries if True

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not inquiry:
        return False, f"❌ Обращение ID {inquiry_id} не найдено"

    if not allow_closed and inquiry.status == InquiryStatus.CLOSED:
        return False, "❌ Это обращение уже закрыто"

    return True, None


def validate_inquiry_assignment(
    inquiry: UserInquiry,
    admin_id: int,
) -> tuple[bool, str | None]:
    """
    Validate inquiry assignment.

    Args:
        inquiry: UserInquiry object
        admin_id: Admin ID to check

    Returns:
        Tuple of (is_valid, error_message)
    """
    if inquiry.assigned_admin_id and inquiry.assigned_admin_id != admin_id:
        return False, "❌ Обращение уже назначено другому админу"
    return True, None
