"""
Phone Update Handlers.

Handles phone number updates.
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.validators.common import validate_phone
from bot.keyboards.reply import contact_input_keyboard, settings_keyboard
from bot.states.profile_update import ProfileUpdateStates

from .utils import get_user_or_error, navigate_to_home

router = Router(name="contact_update_phone")


@router.message(ProfileUpdateStates.waiting_for_phone, F.text == "⏭ Пропустить")
async def skip_phone_update(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Skip phone update."""
    state_data = await state.get_data()
    updating_both = state_data.get("updating_both", False)

    if updating_both:
        # Move to email
        user: User | None = data.get("user")
        current_email = user.email if user else "не указан"

        text = (
            f"📧 **Обновление контактов (шаг 2/2)**\n\n"
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
    else:
        # Just finish
        await state.clear()
        await message.answer(
            "✅ Телефон оставлен без изменений",
            reply_markup=settings_keyboard(),
        )


@router.message(ProfileUpdateStates.waiting_for_phone, F.text == "◀️ Назад")
async def back_from_phone(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Go back to contact menu."""
    from .menu import start_update_contacts

    await start_update_contacts(message, session, state, **data)


@router.message(ProfileUpdateStates.waiting_for_phone, F.text == "🏠 Главное меню")
async def home_from_phone(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Go to main menu from phone input."""
    await navigate_to_home(message, session, state, **data)


@router.message(ProfileUpdateStates.waiting_for_phone)
async def process_phone_update(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Process phone number update.

    Args:
        message: Telegram message
        session: Database session
        state: FSM state
        **data: Handler data
    """
    user = await get_user_or_error(message, state, **data)
    if not user:
        return

    phone = message.text.strip() if message.text else None

    if not phone:
        await message.answer("❌ Пожалуйста, введите номер телефона")
        return

    # Validate phone using common validator
    is_valid, phone_clean, error_message = validate_phone(phone)

    if not is_valid:
        await message.answer(
            f"❌ {error_message}\n\n"
            f"Попробуйте еще раз или нажмите '⏭ Пропустить'"
        )
        return

    # Update phone
    from app.repositories.user_repository import UserRepository

    user_repo = UserRepository(session)
    await user_repo.update(user.id, phone=phone_clean)
    await session.commit()

    # Check if updating both
    state_data = await state.get_data()
    updating_both = state_data.get("updating_both", False)

    if updating_both:
        # Move to email
        current_email = user.email or "не указан"

        text = (
            f"✅ Телефон обновлен: `{phone_clean}`\n\n"
            f"📧 **Обновление контактов (шаг 2/2)**\n\n"
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
    else:
        # Just finish
        await state.clear()

        text = (
            f"✅ **Телефон успешно обновлен!**\n\n"
            f"📞 Новый номер: `{phone_clean}`\n\n"
            f"💡 Данные сохранены в вашем профиле."
        )

        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=settings_keyboard(),
        )
