"""
Contact Update Menu Handlers.

Handles menu navigation and contact type selection.
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.reply import (
    contact_input_keyboard,
    contact_update_menu_keyboard,
    settings_keyboard,
)
from bot.states.profile_update import ProfileUpdateStates

from .utils import get_user_or_error, navigate_to_home

router = Router(name="contact_update_menu")


@router.message(StateFilter('*'), F.text == "📝 Обновить контакты")
async def start_update_contacts(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Start contact update flow with menu.

    Args:
        message: Telegram message
        session: Database session
        state: FSM state
        **data: Handler data
    """
    user = await get_user_or_error(message, state, **data)
    if not user:
        return

    await state.clear()

    # Show current contacts
    phone_display = user.phone or "не указан"
    email_display = user.email or "не указан"

    text = (
        f"📝 *Обновление контактов*\n\n"
        f"📋 **Текущие контакты:**\n"
        f"📞 Телефон: `{phone_display}`\n"
        f"📧 Email: `{email_display}`\n\n"
        f"Что вы хотите обновить?"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=contact_update_menu_keyboard(),
    )
    await state.set_state(ProfileUpdateStates.choosing_contact_type)


@router.message(
    ProfileUpdateStates.choosing_contact_type, F.text == "◀️ Назад"
)
async def back_from_choice(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Go back from contact choice to settings."""
    await state.clear()

    # Check for language
    from bot.i18n.loader import get_user_language
    from app.models.user import User

    user: User | None = data.get("user")
    language = "ru"
    if user:
        language = await get_user_language(session, user.id)

    await message.answer(
        "⚙️ *Настройки*\n\nВыберите раздел:",
        parse_mode="Markdown",
        reply_markup=settings_keyboard(language),
    )


@router.message(
    ProfileUpdateStates.choosing_contact_type, F.text == "🏠 Главное меню"
)
async def home_from_choice(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Go to main menu from choice."""
    await navigate_to_home(message, session, state, **data)


@router.message(
    ProfileUpdateStates.choosing_contact_type, F.text == "📞 Обновить телефон"
)
async def start_phone_update(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Start phone update."""
    user = await get_user_or_error(message, state, **data)
    if not user:
        return

    current_phone = user.phone or "не указан"

    text = (
        f"📞 **Обновление телефона**\n\n"
        f"Текущий номер: `{current_phone}`\n\n"
        f"Введите новый номер телефона в формате:\n"
        f"`+79991234567` или `89991234567`\n\n"
        f"Или нажмите кнопку ниже:"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=contact_input_keyboard(),
    )
    await state.set_state(ProfileUpdateStates.waiting_for_phone)


@router.message(
    ProfileUpdateStates.choosing_contact_type, F.text == "📧 Обновить email"
)
async def start_email_update(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Start email update."""
    user = await get_user_or_error(message, state, **data)
    if not user:
        return

    current_email = user.email or "не указан"

    text = (
        f"📧 **Обновление email**\n\n"
        f"Текущий email: `{current_email}`\n\n"
        f"Введите новый email адрес в формате:\n"
        f"`example@mail.com`\n\n"
        f"Или нажмите кнопку ниже:"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=contact_input_keyboard(),
    )
    await state.set_state(ProfileUpdateStates.waiting_for_email)


@router.message(
    ProfileUpdateStates.choosing_contact_type, F.text == "📝 Обновить оба"
)
async def start_both_update(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Start updating both contacts."""
    user = await get_user_or_error(message, state, **data)
    if not user:
        return

    current_phone = user.phone or "не указан"

    text = (
        f"📞 **Обновление контактов (шаг 1/2)**\n\n"
        f"Текущий телефон: `{current_phone}`\n\n"
        f"Введите новый номер телефона в формате:\n"
        f"`+79991234567` или `89991234567`\n\n"
        f"Или нажмите кнопку ниже:"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=contact_input_keyboard(),
    )
    # Save flag that we're updating both
    await state.update_data(updating_both=True)
    await state.set_state(ProfileUpdateStates.waiting_for_phone)
