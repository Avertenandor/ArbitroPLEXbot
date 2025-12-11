"""
Admin Action Logs Handler.

Shows recent admin actions for super admin monitoring.
"""

from datetime import datetime
from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.admin_action_repository import AdminActionRepository
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import get_admin_keyboard_from_data


router = Router(name="admin_action_logs")


def escape_markdown(text: str) -> str:
    """Escape special Markdown characters."""
    if not text:
        return text
    # Escape underscores which break Markdown
    return text.replace("_", "\\_")


def format_action_type(action_type: str) -> str:
    """
    Format action type for display.

    Args:
        action_type: Raw action type string

    Returns:
        Formatted action type string with emoji
    """
    action_map = {
        "ADMIN_CREATED": "👤 Создан админ",
        "ADMIN_DELETED": "🗑️ Удален админ",
        "ADMIN_ROLE_CHANGED": "🔄 Изменена роль",
        "ADMIN_BLOCKED": "🚫 Заблокирован админ",
        "ADMIN_UNBLOCKED": "✅ Разблокирован админ",
        "USER_BLOCKED": "🚫 Заблокирован юзер",
        "USER_UNBLOCKED": "✅ Разблокирован юзер",
        "USER_BALANCE_ADJUSTED": "💰 Баланс изменен",
        "WITHDRAWAL_APPROVED": "✅ Вывод одобрен",
        "WITHDRAWAL_REJECTED": "❌ Вывод отклонен",
        "BROADCAST_SENT": "📢 Рассылка отправлена",
        "WALLET_CHANGED": "🔐 Изменен кошелек",
        "MASTER_KEY_CHANGED": "🔑 Изменен мастер-ключ",
        "BLACKLIST_ADDED": "⛔ Добавлен в ЧС",
        "BLACKLIST_REMOVED": "✅ Удален из ЧС",
        "DEPOSIT_APPROVED": "💰 Депозит одобрен",
        "DEPOSIT_REJECTED": "❌ Депозит отклонен",
        "EMERGENCY_STOP_ACTIVATED": "🚨 Аварийная остановка",
        "EMERGENCY_STOP_DEACTIVATED": "✅ Аварийная остановка снята",
    }
    return action_map.get(action_type, action_type)


def format_datetime(dt: datetime) -> str:
    """
    Format datetime for display.

    Args:
        dt: Datetime object

    Returns:
        Formatted datetime string
    """
    return dt.strftime("%d.%m.%Y %H:%M:%S")


def format_action_details(action_type: str, details: dict | None) -> str:
    """
    Format action details for display.

    Args:
        action_type: Action type
        details: Action details dict

    Returns:
        Formatted details string
    """
    if not details:
        return ""

    result = []

    # Common fields
    if "amount" in details:
        result.append(f"💵 {details['amount']} USDT")

    if "reason" in details:
        result.append(f"📝 {escape_markdown(str(details['reason']))}")

    if "old_role" in details and "new_role" in details:
        result.append(f"📊 {details['old_role']} → {details['new_role']}")

    if "username" in details:
        result.append(f"👤 @{escape_markdown(str(details['username']))}")

    if "telegram_id" in details:
        result.append(f"ID: {details['telegram_id']}")

    if "wallet_address" in details:
        wallet = details["wallet_address"]
        if len(wallet) > 20:
            wallet = wallet[:10] + "..." + wallet[-8:]
        result.append(f"💼 {wallet}")

    return "\n   " + "\n   ".join(result) if result else ""


@router.message(StateFilter("*"), F.text == "📋 Логи действий")
async def handle_action_logs(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Show recent admin actions for super admin monitoring.

    Args:
        message: Incoming message
        session: Database session
        **data: Handler data including admin flags
    """
    # Check if user is super admin
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    if not admin.is_super_admin:
        await message.answer(
            "❌ Доступ запрещён. Только для Super Admin.",
            reply_markup=get_admin_keyboard_from_data(data),
        )
        return

    # Get recent admin actions
    action_repo = AdminActionRepository(session)
    actions = await action_repo.get_recent(limit=20)

    if not actions:
        await message.answer(
            "📋 Логи действий админов\n\nНет записей о действиях админов.",
            reply_markup=get_admin_keyboard_from_data(data),
        )
        return

    # Format actions for display
    text = "📋 Логи действий админов (последние 20)\n\n"

    for i, action in enumerate(actions, 1):
        # Admin info - escape underscores for Markdown
        admin_name = escape_markdown(action.admin.username or f"ID:{action.admin.telegram_id}")
        admin_role = action.admin.role_display or action.admin.role

        # Target user info (if applicable)
        target_info = ""
        if action.target_user_id and action.target_user:
            target_name = escape_markdown(action.target_user.username or f"ID:{action.target_user.telegram_id}")
            target_info = f"\n🎯 Цель: @{target_name}"

        # Format action
        action_text = (
            f"{i}. {format_action_type(action.action_type)}\n"
            f"👤 Админ: @{admin_name} ({admin_role})\n"
            f"🕒 {format_datetime(action.created_at)}"
            f"{target_info}"
            f"{format_action_details(action.action_type, action.details)}\n\n"
        )

        text += action_text

    text += f"\n📊 Всего записей: {len(actions)}"

    # Split message if too long
    if len(text) > 4000:
        # Send in chunks
        chunks = []
        current_chunk = "📋 Логи действий админов (последние 20)\n\n"

        for i, action in enumerate(actions, 1):
            admin_name = escape_markdown(action.admin.username or f"ID:{action.admin.telegram_id}")
            admin_role = action.admin.role_display or action.admin.role

            target_info = ""
            if action.target_user_id and action.target_user:
                target_name = escape_markdown(action.target_user.username or f"ID:{action.target_user.telegram_id}")
                target_info = f"\n🎯 Цель: @{target_name}"

            action_text = (
                f"{i}. {format_action_type(action.action_type)}\n"
                f"👤 Админ: @{admin_name} ({admin_role})\n"
                f"🕒 {format_datetime(action.created_at)}"
                f"{target_info}"
                f"{format_action_details(action.action_type, action.details)}\n\n"
            )

            if len(current_chunk) + len(action_text) > 3800:
                chunks.append(current_chunk)
                current_chunk = action_text
            else:
                current_chunk += action_text

        if current_chunk:
            chunks.append(current_chunk)

        # Send chunks
        for chunk in chunks:
            await message.answer(chunk)

        # Send final summary with keyboard
        await message.answer(
            f"📊 Всего записей: {len(actions)}",
            reply_markup=get_admin_keyboard_from_data(data),
        )
    else:
        await message.answer(
            text,
            reply_markup=get_admin_keyboard_from_data(data),
        )
