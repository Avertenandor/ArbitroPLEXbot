"""
Contact verification handlers for registration flow.

Contains handlers for:
- Contact choice
- Phone number input
- Email input
"""

from typing import Any

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.user_service import UserService
from bot.keyboards.reply import main_menu_reply_keyboard
from bot.states.registration import RegistrationStates
from bot.utils.menu_buttons import is_menu_button

from . import messages
from .blacklist_checks import get_blacklist_entry
from .helpers import is_skip_command, normalize_button_text
from .validators import normalize_phone, validate_email, validate_phone


router = Router()


@router.message(RegistrationStates.waiting_for_contacts_choice)
async def handle_contacts_choice(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle contacts choice during registration."""
    # CRITICAL: handle /start here
    if message.text and message.text.startswith("/start"):
        logger.info("handle_contacts_choice: /start caught, clearing state")
        await state.clear()
        return  # Let CommandStart() handle this

    if message.text == "✅ Да, оставить контакты":
        await message.answer(
            messages.PHONE_PROMPT,
            parse_mode="Markdown",
        )
        await state.set_state(RegistrationStates.waiting_for_phone)
    # Normalize text: remove FE0F (emoji variation selector)
    elif message.text and normalize_button_text(message.text) in (
        "⏭ Пропустить", "⏭️ Пропустить"
    ):
        await message.answer(messages.CONTACTS_CHOICE_SKIP)
        await state.clear()
    else:
        # If user sent something else, show menu again
        from bot.keyboards.reply import contacts_choice_keyboard
        await message.answer(
            messages.CONTACTS_CHOICE_PROMPT,
            parse_mode="Markdown",
            reply_markup=contacts_choice_keyboard(),
        )


@router.message(RegistrationStates.waiting_for_phone)
async def process_phone(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Process phone number."""
    # Check if message is a menu button
    if is_menu_button(message.text):
        await state.clear()
        user: User | None = data.get("user")
        is_admin = data.get("is_admin", False)
        blacklist_entry = await get_blacklist_entry(
            user.telegram_id if user else None, session
        )
        await message.answer(
            messages.MAIN_MENU_TEXT,
            reply_markup=main_menu_reply_keyboard(
                user=user,
                blacklist_entry=blacklist_entry,
                is_admin=is_admin,
            ),
        )
        return

    if is_skip_command(message.text):
        await state.update_data(phone=None)
        await state.set_state(RegistrationStates.waiting_for_email)
        await message.answer(messages.EMAIL_PROMPT)
        return

    phone = message.text.strip() if message.text else ""

    # Validate phone
    is_valid, error_msg = validate_phone(phone)
    if not is_valid:
        await message.answer(error_msg, parse_mode="Markdown")
        return

    # Normalize phone
    phone = normalize_phone(phone) if phone else ""

    await state.update_data(phone=phone if phone else None)
    await state.set_state(RegistrationStates.waiting_for_email)

    if phone:
        await message.answer(messages.PHONE_ACCEPTED, parse_mode="Markdown")
    else:
        await message.answer(messages.EMAIL_PROMPT, parse_mode="Markdown")


@router.message(RegistrationStates.waiting_for_email)
async def process_email(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Process email and save contacts."""
    # Check if message is a menu button
    if is_menu_button(message.text):
        await state.clear()
        user: User | None = data.get("user")
        is_admin = data.get("is_admin", False)
        blacklist_entry = await get_blacklist_entry(
            user.telegram_id if user else None, session
        )
        await message.answer(
            messages.MAIN_MENU_TEXT,
            reply_markup=main_menu_reply_keyboard(
                user=user,
                blacklist_entry=blacklist_entry,
                is_admin=is_admin,
            ),
        )
        return

    if is_skip_command(message.text):
        email = None
    else:
        email = message.text.strip().lower() if message.text else None

        # Validate email
        is_valid, error_msg = validate_email(email)
        if not is_valid:
            await message.answer(error_msg, parse_mode="Markdown")
            return

    # Get phone from state
    state_data = await state.get_data()
    phone = state_data.get("phone")

    # Update user with contacts
    user_service = UserService(session)
    current_user: User | None = data.get("user")
    if not current_user:
        logger.error("process_email: user missing in middleware data")
        await message.answer(
            "❌ Ошибка контекста пользователя. Повторите /start"
        )
        return
    await user_service.update_profile(
        current_user.id,
        phone=phone,
        email=email,
    )

    contacts_text = "✅ Контакты сохранены!\n\n"
    if phone:
        contacts_text += f"📞 Телефон: {phone}\n"
    if email:
        contacts_text += f"📧 Email: {email}\n"

    if not phone and not email:
        contacts_text = messages.CONTACTS_SKIPPED
    else:
        contacts_text += "\nВы можете изменить их позже в настройках профиля."

    # Get is_admin from middleware data
    is_admin = data.get("is_admin", False)
    blacklist_entry = await get_blacklist_entry(current_user.telegram_id, session)
    await message.answer(
        contacts_text,
        reply_markup=main_menu_reply_keyboard(
            user=current_user,
            blacklist_entry=blacklist_entry,
            is_admin=is_admin,
        ),
    )
    await state.clear()
