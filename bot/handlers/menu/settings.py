"""
Settings menu handlers.

This module contains handlers for displaying the settings menu.
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from bot.keyboards.reply import settings_keyboard
from bot.utils.user_loader import UserLoader

router = Router()


@router.message(StateFilter('*'), F.text == "⚙️ Настройки")
async def show_settings_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show settings menu."""
    telegram_id = message.from_user.id if message.from_user else None
    user: User | None = data.get("user")
    if not user and telegram_id:
        user = await UserLoader.get_user_by_telegram_id(session, telegram_id)
    if not user:
        await message.answer(
            "⚠️ Ошибка: не удалось загрузить данные пользователя. "
            "Попробуйте отправить /start"
        )
        return

    await state.clear()

    text = "⚙️ *Настройки*\n\nВыберите раздел:"

    await message.answer(
        text, reply_markup=settings_keyboard(), parse_mode="Markdown"
    )
