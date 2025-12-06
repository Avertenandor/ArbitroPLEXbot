"""
Email Update Handlers.

Handles email address updates.
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.validators.common import validate_email
from bot.keyboards.reply import contact_input_keyboard, settings_keyboard
from bot.states.profile_update import ProfileUpdateStates

from .utils import get_user_or_error, navigate_to_home

router = Router(name="contact_update_email")


@router.message(ProfileUpdateStates.waiting_for_email, F.text == "⏭ Пропустить")
async def skip_email_update(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Skip email update."""
    await state.clear()
    await message.answer(
        "✅ Email оставлен без изменений",
        reply_markup=settings_keyboard(),
    )


@router.message(ProfileUpdateStates.waiting_for_email, F.text == "◀️ Назад")
async def back_from_email(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Go back to contact menu."""
    from .menu import start_update_contacts

    await start_update_contacts(message, session, state, **data)


@router.message(ProfileUpdateStates.waiting_for_email, F.text == "🏠 Главное меню")
async def home_from_email(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Go to main menu from email input."""
    await navigate_to_home(message, session, state, **data)


@router.message(ProfileUpdateStates.waiting_for_email)
async def process_email_update(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Process email update.

    Args:
        message: Telegram message
        session: Database session
        state: FSM state
        **data: Handler data
    """
    user = await get_user_or_error(message, state, **data)
    if not user:
        return

    email = message.text.strip() if message.text else None

    if not email:
        await message.answer("❌ Пожалуйста, введите email адрес")
        return

    # Validate email using common validator
    is_valid, email_normalized, error_message = validate_email(email)

    if not is_valid:
        await message.answer(
            f"❌ {error_message}\n\n"
            f"Попробуйте еще раз или нажмите '⏭ Пропустить'",
            parse_mode="Markdown",
        )
        return

    # Update email
    from app.repositories.user_repository import UserRepository

    user_repo = UserRepository(session)
    await user_repo.update(user.id, email=email_normalized)
    await session.commit()

    await state.clear()

    # Show final result
    user_updated = await user_repo.get_by_id(user.id)
    phone_display = (
        user_updated.phone
        if user_updated and user_updated.phone
        else "не указан"
    )
    email_display = (
        user_updated.email
        if user_updated and user_updated.email
        else "не указан"
    )

    text = (
        f"✅ **Контакты успешно обновлены!**\n\n"
        f"📋 **Ваши контакты:**\n"
        f"📞 Телефон: `{phone_display}`\n"
        f"📧 Email: `{email_display}`\n\n"
        f"💡 Эти данные сохранены в вашем профиле и доступны администраторам."
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=settings_keyboard(),
    )
