"""
AI Appeals Operations.

Write operations for appeals (take, resolve, reply).
"""

from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appeal import Appeal, AppealStatus
from app.services.ai_appeals_formatter import (
    format_admin_identifier,
    format_message_preview,
    format_reply_message,
)
from app.services.ai_appeals_helpers import (
    fetch_user_for_appeal,
    format_decision_result,
    get_user_info,
    process_blacklist_unblock,
    validate_decision,
)
from app.utils.formatters import format_user_identifier


async def take_appeal_for_review(
    session: AsyncSession,
    admin: Any,
    appeal_id: int,
) -> dict[str, Any]:
    """
    Take appeal for review (set status to under_review).

    Args:
        session: Database session
        admin: Admin model instance
        appeal_id: Appeal ID

    Returns:
        Result dict
    """
    # Get appeal
    stmt = select(Appeal).where(Appeal.id == appeal_id)
    result = await session.execute(stmt)
    appeal = result.scalar_one_or_none()

    if not appeal:
        error_text = f"❌ Обращение ID {appeal_id} не найдено"
        return {"success": False, "error": error_text}

    if appeal.status != AppealStatus.PENDING:
        error_msg = (
            f"❌ Обращение уже имеет статус '{appeal.status}'. "
            "Взять можно только 'pending'."
        )
        return {
            "success": False,
            "error": error_msg
        }

    # Update appeal
    appeal.status = AppealStatus.UNDER_REVIEW
    appeal.reviewed_by_admin_id = admin.id

    await session.commit()

    logger.info(
        f"AI APPEALS: Admin {admin.telegram_id} (@{admin.username}) "
        f"took appeal {appeal_id} for review"
    )

    admin_name = format_admin_identifier(admin)

    return {
        "success": True,
        "appeal_id": appeal_id,
        "new_status": "under_review",
        "admin": admin_name,
        "message": (
            f"✅ Обращение #{appeal_id} взято на рассмотрение"
        )
    }


async def resolve_appeal_with_decision(
    session: AsyncSession,
    admin: Any,
    appeal_id: int,
    decision: str,
    notes: str | None = None,
) -> dict[str, Any]:
    """
    Resolve appeal (approve or reject).

    Args:
        session: Database session
        admin: Admin model instance
        appeal_id: Appeal ID
        decision: "approve" or "reject"
        notes: Optional review notes

    Returns:
        Result dict
    """
    # Validate decision
    is_valid, error_msg = validate_decision(decision)
    if not is_valid:
        return {"success": False, "error": error_msg}

    # Get appeal
    stmt = select(Appeal).where(Appeal.id == appeal_id)
    result = await session.execute(stmt)
    appeal = result.scalar_one_or_none()

    if not appeal:
        error_text = f"❌ Обращение ID {appeal_id} не найдено"
        return {"success": False, "error": error_text}

    if appeal.status in [AppealStatus.APPROVED, AppealStatus.REJECTED]:
        error_text = (
            f"❌ Обращение уже закрыто со статусом "
            f"'{appeal.status}'"
        )
        return {
            "success": False,
            "error": error_text
        }

    # Update appeal
    new_status = (
        AppealStatus.APPROVED
        if decision == "approve"
        else AppealStatus.REJECTED
    )
    appeal.status = new_status
    appeal.reviewed_by_admin_id = admin.id
    appeal.reviewed_at = datetime.now(UTC)
    appeal.review_notes = (
        f"[АРЬЯ] {notes}"
        if notes
        else "[АРЬЯ] Решение принято через AI-ассистента"
    )

    # If approved, unblock user from blacklist
    if decision == "approve":
        await process_blacklist_unblock(
            session,
            appeal,
            appeal_id
        )

    await session.commit()

    # Get user info and format decision
    user_info, _ = await get_user_info(session, appeal.user_id)
    decision_emoji, decision_text = format_decision_result(decision)

    logger.info(
        f"AI APPEALS: Admin {admin.telegram_id} (@{admin.username}) "
        f"{decision_text} appeal {appeal_id} for user {user_info}"
    )

    result_msg = f"{decision_emoji} Обращение #{appeal_id} {decision_text}"
    if decision == "approve":
        result_msg += "\n🔓 Пользователь разблокирован"

    admin_name = format_admin_identifier(admin)

    return {
        "success": True,
        "appeal_id": appeal_id,
        "user": user_info,
        "decision": decision,
        "new_status": new_status,
        "notes": notes,
        "admin": admin_name,
        "message": result_msg
    }


async def send_reply_to_appeal(
    session: AsyncSession,
    admin: Any,
    appeal_id: int,
    message: str,
    bot: Any = None,
) -> dict[str, Any]:
    """
    Send reply message to user who submitted the appeal.

    Args:
        session: Database session
        admin: Admin model instance
        appeal_id: Appeal ID
        message: Message text to send
        bot: Bot instance for sending

    Returns:
        Result dict
    """
    if not bot:
        return {"success": False, "error": "❌ Бот не инициализирован"}

    if not message or len(message) < 5:
        error_msg = (
            "❌ Сообщение должно содержать "
            "минимум 5 символов"
        )
        return {"success": False, "error": error_msg}

    # Get appeal
    stmt = select(Appeal).where(Appeal.id == appeal_id)
    result = await session.execute(stmt)
    appeal = result.scalar_one_or_none()

    if not appeal:
        error_text = f"❌ Обращение ID {appeal_id} не найдено"
        return {"success": False, "error": error_text}

    # Get user
    user = await fetch_user_for_appeal(session, appeal)

    if not user or not user.telegram_id:
        error_msg = (
            "❌ Не удалось найти пользователя для отправки"
        )
        return {"success": False, "error": error_msg}

    # Format message
    admin_name = (
        f"@{admin.username}"
        if admin.username
        else "Администратор"
    )
    formatted_message = format_reply_message(
        appeal_id,
        message,
        admin_name
    )

    # Send message
    try:
        await bot.send_message(
            chat_id=user.telegram_id,
            text=formatted_message,
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(
            f"Failed to send reply to appeal {appeal_id}: {e}"
        )
        error_text = f"❌ Не удалось отправить: {str(e)}"
        return {"success": False, "error": error_text}

    user_info = format_user_identifier(user)
    message_preview = format_message_preview(message, max_length=50)

    logger.info(
        f"AI APPEALS: Admin {admin.telegram_id} replied to appeal "
        f"{appeal_id}: {message_preview}..."
    )

    message_sent = format_message_preview(message)

    return {
        "success": True,
        "appeal_id": appeal_id,
        "user": user_info,
        "message_sent": message_sent,
        "message": "✅ Ответ отправлен пользователю"
    }
