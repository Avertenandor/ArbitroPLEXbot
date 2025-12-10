"""
Language settings handlers.

This module contains handlers for managing user language preferences.
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repository import UserRepository
from bot.i18n.loader import get_user_language
from bot.keyboards.reply import settings_keyboard


router = Router()


@router.message(StateFilter('*'), F.text == "🌐 Изменить язык")
async def show_language_settings(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Show language selection menu.

    Args:
        message: Telegram message
        session: Database session
        state: FSM state
        **data: Handler data
    """
    user: User | None = data.get("user")
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return

    await state.clear()

    # Get current language
    current_language = await get_user_language(session, user.id)

    text = (
        f"🌐 *Настройка языка*\n\n"
        f"Текущий язык: **{current_language.upper()}**\n\n"
        f"Выберите язык интерфейса:"
    )

    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🇷🇺 Русский"))
    builder.row(KeyboardButton(text="🇬🇧 English"))
    builder.row(KeyboardButton(text="◀️ Назад"))

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=builder.as_markup(resize_keyboard=True),
    )


@router.message(F.text.in_({"🇷🇺 Русский", "🇬🇧 English"}))
async def process_language_selection(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Process language selection.

    Args:
        message: Telegram message
        session: Database session
        **data: Handler data
    """
    user: User | None = data.get("user")
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return

    # Determine selected language
    language = "ru" if message.text == "🇷🇺 Русский" else "en"

    # Update user language
    user_repo = UserRepository(session)
    await user_repo.update(user.id, language=language)
    await session.commit()

    # Show confirmation
    if language == "ru":
        text = "✅ Язык интерфейса изменен на **Русский**"
    else:
        text = "✅ Interface language changed to **English**"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=settings_keyboard(language),
    )


@router.message(StateFilter('*'), F.text == "◀️ Назад")
async def back_to_settings_from_language(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Handle back button from language menu.

    Args:
        message: Telegram message
        session: Database session
        state: FSM state
        **data: Handler data
    """
    # If we are in a specific state that handles "◀️ Назад" differently,
    # this handler might not be reached if registered after.
    # But here we use it as a catch-all for this button in menu router.

    # Clear state just in case
    await state.clear()

    # Import to avoid circular dependency
    from bot.handlers.menu.settings import show_settings_menu

    # Redirect to settings menu
    await show_settings_menu(message, session, state, **data)
