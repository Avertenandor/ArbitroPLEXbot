"""
Additional action handlers for user messages viewing.

This module handles actions like viewing statistics, deleting messages,
and returning to the admin panel.
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


router = Router(name="admin_user_messages_actions")


@router.message(
    AdminUserMessagesStates.viewing_messages,
    F.text == "📊 Статистика"
)
async def show_messages_stats(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show statistics for current user's messages."""
    is_admin = data.get("is_admin", False)
    admin: Admin | None = data.get("admin")

    if not is_admin or not admin:
        await message.answer("❌ Доступ запрещен")
        return

    state_data = await state.get_data()
    telegram_id = state_data.get("telegram_id")

    if not telegram_id:
        await message.answer("❌ Ошибка: не найден ID пользователя")
        return

    # Get user info
    user_service = UserService(session)
    user = await user_service.get_user_by_telegram_id(telegram_id)

    # Get message stats
    msg_service = UserMessageLogService(session)
    stats = await msg_service.get_user_message_stats(telegram_id)

    username = user.username if user else "N/A"
    text = (
        f"📊 **Статистика сообщений**\n\n"
        f"👤 Пользователь: @{username}\n"
        f"🆔 Telegram ID: `{telegram_id}`\n\n"
        f"📝 Всего сообщений: **{stats.get('total', 0)}**\n"
        f"📅 За сегодня: **{stats.get('today', 0)}**\n"
        f"📆 За неделю: **{stats.get('week', 0)}**\n"
        f"📆 За месяц: **{stats.get('month', 0)}**\n\n"
        f"🕒 Первое сообщение: {stats.get('first_message', 'N/A')}\n"
        f"🕒 Последнее сообщение: {stats.get('last_message', 'N/A')}\n"
    )

    is_super_admin = data.get("is_super_admin", False)
    total = state_data.get("total", 0)
    page = state_data.get("page", 0)
    page_size = state_data.get("page_size", 50)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    has_prev = page > 0
    has_next = page < total_pages - 1

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=user_messages_navigation_keyboard(
            has_prev=has_prev,
            has_next=has_next,
            is_super_admin=is_super_admin,
        ),
    )


@router.message(
    AdminUserMessagesStates.viewing_messages,
    F.text == "🗑 Удалить все сообщения"
)
async def delete_user_messages(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Delete all messages for user."""
    is_admin = data.get("is_admin", False)
    admin: Admin | None = data.get("admin")
    is_super_admin = data.get("is_super_admin", False)

    if not is_admin or not admin:
        await message.answer("❌ Доступ запрещен")
        return

    # Only super admin can delete
    if not is_super_admin:
        await message.answer("❌ Только супер-администратор может удалять сообщения")
        return

    # Get telegram_id from state
    state_data = await state.get_data()
    telegram_id = state_data.get("telegram_id")

    if not telegram_id:
        await message.answer("❌ Ошибка: не найден ID пользователя")
        return

    # Delete messages
    msg_service = UserMessageLogService(session)
    count = await msg_service.delete_all_messages(telegram_id)
    await session.commit()

    await clear_state_preserve_admin_token(state)

    await message.answer(
        f"✅ Все сообщения пользователя `{telegram_id}` удалены.\n\n"
        f"Удалено: {count} сообщений",
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard_from_data(data),
    )
    logger.warning(
        f"Admin {admin.id} deleted {count} messages for user {telegram_id}"
    )


@router.message(
    AdminUserMessagesStates.viewing_messages,
    F.text == "◀️ Назад в админ-панель"
)
async def back_to_admin_panel_from_messages(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Return to admin panel from message viewing."""
    await clear_state_preserve_admin_token(state)

    await message.answer(
        "👑 **Панель администратора**\n\n"
        "Выберите действие:",
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard_from_data(data),
    )
