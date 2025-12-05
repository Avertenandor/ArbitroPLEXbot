"""
Helper functions for user messages handlers.

This module contains utility functions for navigation, user search,
and message formatting used across the user messages feature.
"""

from typing import Any

from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service import UserService
from bot.keyboards.reply import get_admin_keyboard_from_data
from bot.utils.admin_utils import clear_state_preserve_admin_token


async def check_navigation_buttons(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> bool:
    """
    Check for navigation buttons and handle them.

    Returns True if navigation button was pressed.
    """
    # Breakout for financial reports (navigation fix)
    if message.text and "Финансовая" in message.text:
        await clear_state_preserve_admin_token(state)
        from bot.handlers.admin.financials import show_financial_list
        await show_financial_list(message, session, state, **data)
        return True

    # Check for cancel/back
    if message.text in ("◀️ Назад в админ-панель", "❌ Отмена"):
        await clear_state_preserve_admin_token(state)
        await message.answer(
            "👑 **Панель администратора**\n\nВыберите действие:",
            parse_mode="Markdown",
            reply_markup=get_admin_keyboard_from_data(data),
        )
        return True

    return False


async def find_user_by_query(
    search_query: str,
    user_service: UserService,
) -> tuple[Any | None, int | None]:
    """
    Find user by various search methods.

    Returns:
        Tuple of (user, telegram_id)
    """
    # Search by username with @
    if search_query.startswith("@"):
        username = search_query.lstrip("@")
        user = await user_service.find_by_username(username)
        return (user, user.telegram_id) if user else (None, None)

    # Search by wallet address
    if search_query.startswith("0x") and len(search_query) == 42:
        user = await user_service.get_by_wallet(search_query)
        return (user, user.telegram_id) if user else (None, None)

    # Try as numeric ID
    try:
        numeric_id = int(search_query)
        # Try as telegram_id first
        user = await user_service.get_user_by_telegram_id(numeric_id)
        if user:
            return user, user.telegram_id

        # Try as user_id
        user = await user_service.get_by_id(numeric_id)
        return (user, user.telegram_id) if user else (None, None)

    except ValueError:
        # Try as username without @
        user = await user_service.find_by_username(search_query)
        return (user, user.telegram_id) if user else (None, None)


def format_messages_list(
    user: Any,
    telegram_id: int,
    messages: list,
    total: int,
) -> str:
    """Format messages list for display."""
    text_lines = [
        f"📝 **Сообщения пользователя {user.username or telegram_id}**",
        f"Telegram ID: `{telegram_id}`",
        f"Всего сообщений: {total}",
        f"Показано: {min(len(messages), 20)}",
        "",
        "---",
        "",
    ]

    for msg in messages[:20]:  # Show first 20
        timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        msg_text = msg.message_text
        if len(msg_text) > 100:
            msg_text = msg_text[:100] + "..."
        text_lines.append(f"🕒 {timestamp}")
        text_lines.append(f"💬 `{msg_text}`")
        text_lines.append("")

    return "\n".join(text_lines)
