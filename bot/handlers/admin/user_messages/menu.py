"""
Menu entry point for user messages viewing feature.

This module handles the main menu entry point where admins can
access the user messages viewing functionality.
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin
from bot.keyboards.reply import get_admin_keyboard_from_data
from bot.states.admin import AdminUserMessagesStates
from bot.utils.admin_utils import clear_state_preserve_admin_token


router = Router(name="admin_user_messages_menu")


@router.message(F.text == "📝 Просмотр сообщений пользователей")
async def show_user_messages_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Show user messages menu.

    Only accessible to admins.
    """
    is_admin = data.get("is_admin", False)
    admin: Admin | None = data.get("admin")

    if not is_admin or not admin:
        await message.answer("❌ Эта функция доступна только администраторам")
        return

    await clear_state_preserve_admin_token(state)

    text = """
📝 **Просмотр сообщений пользователей**

Здесь вы можете просмотреть текстовые сообщения, отправленные пользователями боту.

🔍 **Поиск пользователя:**
• Telegram ID: `1040687384`
• Username: `@username`
• ID пользователя: `123`
• Кошелек: `0x...`

_Введите любой из этих идентификаторов:_
    """.strip()

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard_from_data(data),
    )
    await state.set_state(AdminUserMessagesStates.waiting_for_user_id)
    logger.info(f"Admin {admin.id} opened user messages menu")
