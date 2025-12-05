"""
User search and ID processing for user messages viewing.

This module handles the user search functionality, allowing admins
to find users by various identifiers (Telegram ID, username, wallet, etc.)
and display their messages.
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin
from app.services.user_message_log_service import UserMessageLogService
from app.services.user_service import UserService
from bot.keyboards.reply import (
    get_admin_keyboard_from_data,
    user_messages_navigation_keyboard,
)
from bot.states.admin import AdminUserMessagesStates
from bot.utils.admin_utils import clear_state_preserve_admin_token

from .helpers import check_navigation_buttons, find_user_by_query, format_messages_list

router = Router(name="admin_user_messages_search")


@router.message(AdminUserMessagesStates.waiting_for_user_id)
async def process_user_id_for_messages(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Process user ID and show messages."""
    is_admin = data.get("is_admin", False)
    admin: Admin | None = data.get("admin")

    if not is_admin or not admin:
        await message.answer("❌ Эта функция доступна только администраторам")
        return

    # Check for navigation buttons
    if await check_navigation_buttons(message, session, state, **data):
        return

    # Find user by search query
    user_service = UserService(session)
    search_query = message.text.strip()
    user, telegram_id = await find_user_by_query(search_query, user_service)

    if not user or not telegram_id:
        await message.answer(
            f"⚠️ Пользователь по запросу `{search_query}` не найден.\n\n"
            f"Попробуйте:\n"
            f"• Telegram ID (число)\n"
            f"• @username\n"
            f"• ID пользователя (число)\n"
            f"• Адрес кошелька (0x...)",
            parse_mode="Markdown",
            reply_markup=get_admin_keyboard_from_data(data),
        )
        return

    # Get messages
    msg_service = UserMessageLogService(session)
    page = 0
    page_size = 50
    messages, total = await msg_service.get_user_messages(
        telegram_id=telegram_id,
        limit=page_size,
        offset=page * page_size,
    )

    if not messages:
        await message.answer(
            f"📝 **Сообщения пользователя {user.username or telegram_id}**\n\n"
            f"Пользователь еще не отправлял текстовых сообщений боту.\n\n"
            f"_Логируются только текстовые сообщения, не кнопки._",
            parse_mode="Markdown",
            reply_markup=get_admin_keyboard_from_data(data),
        )
        await clear_state_preserve_admin_token(state)
        return

    # Format and send messages
    text = format_messages_list(user, telegram_id, messages, total)

    # Save state for pagination
    await state.set_state(AdminUserMessagesStates.viewing_messages)
    await state.update_data(
        telegram_id=telegram_id,
        page=page,
        total=total,
        page_size=page_size,
    )

    # Check if there are more pages
    total_pages = (total + page_size - 1) // page_size
    has_prev = page > 0
    has_next = page < total_pages - 1
    is_super_admin = data.get("is_super_admin", False)

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=user_messages_navigation_keyboard(
            has_prev=has_prev,
            has_next=has_next,
            is_super_admin=is_super_admin,
        ),
    )
    logger.info(
        f"Admin {admin.id} viewed messages for user {telegram_id} "
        f"(total: {total}, page: {page})"
    )


@router.message(
    AdminUserMessagesStates.viewing_messages,
    F.text == "🔍 Другой пользователь"
)
async def search_another_user(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Search for another user's messages."""
    is_admin = data.get("is_admin", False)
    if not is_admin:
        await message.answer("❌ Доступ запрещен")
        return

    await state.set_state(AdminUserMessagesStates.waiting_for_user_id)
    await message.answer(
        "🔍 **Поиск сообщений пользователя**\n\n"
        "Введите Telegram ID, @username или ID пользователя:\n\n"
        "_Например: 1040687384 или @username_",
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard_from_data(data),
    )
