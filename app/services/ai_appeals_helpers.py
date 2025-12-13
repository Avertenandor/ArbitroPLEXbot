"""
AI Appeals Helpers.

Helper functions for appeals data retrieval and processing.
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appeal import Appeal
from app.models.blacklist import Blacklist
from app.models.user import User
from app.repositories.admin_repository import AdminRepository
from app.services.ai_appeals_formatter import format_admin_identifier
from app.utils.formatters import format_user_identifier


async def fetch_users_batch(
    session: AsyncSession,
    user_ids: list[int]
) -> dict[int, Any]:
    """
    Fetch multiple users by IDs in a single query.

    Args:
        session: Database session
        user_ids: List of user IDs to fetch

    Returns:
        Dict mapping user_id to User model
    """
    if not user_ids:
        return {}

    stmt = select(User).where(User.id.in_(user_ids))
    result = await session.execute(stmt)
    users = result.scalars().all()

    return {user.id: user for user in users}


async def get_user_info(
    session: AsyncSession,
    user_id: int | None
) -> tuple[str, int | None]:
    """
    Get formatted user information.

    Args:
        session: Database session
        user_id: User ID

    Returns:
        Tuple of (formatted_user_info, telegram_id)
    """
    if not user_id:
        return f"User#{user_id}", None

    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        user_info = format_user_identifier(user)
        return user_info, user.telegram_id

    return f"User#{user_id}", None


async def get_reviewer_info(
    session: AsyncSession,
    admin_id: int | None
) -> str | None:
    """
    Get formatted reviewer information.

    Args:
        session: Database session
        admin_id: Admin ID who reviewed

    Returns:
        Formatted reviewer identifier or None
    """
    if not admin_id:
        return None

    admin_repo = AdminRepository(session)
    reviewer = await admin_repo.get_by_id(admin_id)

    if reviewer:
        return format_admin_identifier(reviewer, use_telegram_id=False)

    return None


async def count_appeals_by_status(
    session: AsyncSession
) -> dict[str, int]:
    """
    Count appeals grouped by status.

    Args:
        session: Database session

    Returns:
        Dict with status counts
    """
    stmt = (
        select(Appeal.status, func.count(Appeal.id))
        .group_by(Appeal.status)
    )
    result = await session.execute(stmt)
    counts = {row[0]: row[1] for row in result.all()}

    return {
        "pending": counts.get("pending", 0),
        "under_review": counts.get("under_review", 0),
        "approved": counts.get("approved", 0),
        "rejected": counts.get("rejected", 0),
    }


async def fetch_user_for_appeal(
    session: AsyncSession,
    appeal: Any
) -> Any | None:
    """
    Fetch user associated with an appeal.

    Args:
        session: Database session
        appeal: Appeal model instance

    Returns:
        User model or None
    """
    if not appeal.user_id:
        return None

    stmt = select(User).where(User.id == appeal.user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def validate_status_filter(status: str | None) -> tuple[bool, str | None]:
    """
    Validate status filter value.

    Args:
        status: Status string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not status:
        return True, None

    valid_statuses = ["pending", "under_review", "approved", "rejected"]

    if status.lower() not in valid_statuses:
        error_msg = (
            f"❌ Неверный статус. "
            f"Допустимые: {', '.join(valid_statuses)}"
        )
        return False, error_msg

    return True, None


def validate_decision(decision: str) -> tuple[bool, str | None]:
    """
    Validate decision value.

    Args:
        decision: Decision string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if decision not in ["approve", "reject"]:
        error_msg = (
            "❌ Решение должно быть 'approve' (одобрить) "
            "или 'reject' (отклонить)"
        )
        return False, error_msg

    return True, None


def format_decision_result(decision: str) -> tuple[str, str]:
    """
    Format decision result messages.

    Args:
        decision: Decision ("approve" or "reject")

    Returns:
        Tuple of (emoji, text)
    """
    if decision == "approve":
        return "✅", "одобрено"
    return "❌", "отклонено"


async def process_blacklist_unblock(
    session: AsyncSession,
    appeal: Any,
    appeal_id: int
) -> None:
    """
    Unblock user from blacklist when appeal is approved.

    Args:
        session: Database session
        appeal: Appeal model instance
        appeal_id: Appeal ID for notes
    """
    if not appeal.blacklist_id:
        return

    stmt = select(Blacklist).where(Blacklist.id == appeal.blacklist_id)
    result = await session.execute(stmt)
    blacklist = result.scalar_one_or_none()

    if blacklist:
        blacklist.is_active = False
        note_text = (
            f"\n[АРЬЯ] Разблокирован по обращению "
            f"#{appeal_id}"
        )
        blacklist.notes = (blacklist.notes or "") + note_text
