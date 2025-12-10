"""
Pagination handlers for user messages viewing.

This module handles pagination of user messages, allowing admins to
navigate through pages of messages for a specific user.
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
from bot.keyboards.reply import user_messages_navigation_keyboard
from bot.states.admin import AdminUserMessagesStates


router = Router(name="admin_user_messages_pagination")


@router.message(
    AdminUserMessagesStates.viewing_messages,
    F.text == "⬅️ Предыдущая страница"
)
async def prev_page_user_messages(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show previous page of user messages."""
    is_admin = data.get("is_admin", False)
    admin: Admin | None = data.get("admin")

    if not is_admin or not admin:
        await message.answer("❌ Доступ запрещен")
        return

    # Get state data
    state_data = await state.get_data()
    telegram_id = state_data.get("telegram_id")
    current_page = state_data.get("page", 0)
    total = state_data.get("total", 0)
    page_size = state_data.get("page_size", 50)

    if current_page <= 0:
        await message.answer("📝 Вы уже на первой странице")
        return

    new_page = current_page - 1
    await show_messages_page(
        message, session, state, telegram_id, new_page, page_size, total, admin, **data
    )


@router.message(
    AdminUserMessagesStates.viewing_messages,
    F.text == "➡️ Следующая страница"
)
async def next_page_user_messages(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show next page of user messages."""
    is_admin = data.get("is_admin", False)
    admin: Admin | None = data.get("admin")

    if not is_admin or not admin:
        await message.answer("❌ Доступ запрещен")
        return

    # Get state data
    state_data = await state.get_data()
    telegram_id = state_data.get("telegram_id")
    current_page = state_data.get("page", 0)
    total = state_data.get("total", 0)
    page_size = state_data.get("page_size", 50)

    total_pages = (total + page_size - 1) // page_size
    if current_page >= total_pages - 1:
        await message.answer("📝 Вы уже на последней странице")
        return

    new_page = current_page + 1
    await show_messages_page(
        message, session, state, telegram_id, new_page, page_size, total, admin, **data
    )


async def show_messages_page(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    telegram_id: int,
    page: int,
    page_size: int,
    total: int,
    admin: Admin,
    **data: Any,
) -> None:
    """Show specific page of messages."""
    offset = page * page_size

    # Get messages
    msg_service = UserMessageLogService(session)
    messages, _ = await msg_service.get_user_messages(
        telegram_id=telegram_id,
        limit=page_size,
        offset=offset,
    )

    if not messages:
        await message.answer("📝 Нет сообщений на этой странице")
        return

    # Get user info
    user_service = UserService(session)
    user = await user_service.get_user_by_telegram_id(telegram_id)

    # Format messages
    total_pages = (total + page_size - 1) // page_size
    text_lines = [
        f"📝 **Сообщения пользователя {user.username if user else telegram_id}**",
        f"Telegram ID: `{telegram_id}`",
        f"Всего сообщений: {total}",
        f"Страница: {page + 1}/{total_pages}",
        "",
        "---",
        "",
    ]

    for msg in messages[:20]:
        timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        msg_text = msg.message_text
        if len(msg_text) > 100:
            msg_text = msg_text[:100] + "..."
        text_lines.append(f"🕒 {timestamp}")
        text_lines.append(f"💬 `{msg_text}`")
        text_lines.append("")

    text = "\n".join(text_lines)

    # Update state
    await state.update_data(page=page)

    # Check pagination
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
        f"Admin {admin.id} viewed page {page} of messages "
        f"for user {telegram_id}"
    )
