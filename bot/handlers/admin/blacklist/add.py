"""
Add to blacklist handlers.

Implements the flow for adding users to the blacklist.
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.blacklist_service import BlacklistService
from app.validators.common import validate_telegram_id, validate_wallet_address
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import (
    admin_blacklist_keyboard,
    cancel_keyboard,
)
from bot.states.admin import BlacklistStates
from bot.utils.admin_utils import clear_state_preserve_admin_token


router = Router()


@router.message(F.text == "➕ Добавить в черный список")
async def start_add_to_blacklist(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Start adding to blacklist."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    await message.answer(
        "➕ **Добавление в черный список**\n\n"
        "Введите Telegram ID или BSC wallet address:",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )

    await state.set_state(BlacklistStates.waiting_for_identifier)


@router.message(BlacklistStates.waiting_for_identifier)
async def process_blacklist_identifier(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Process identifier for blacklist."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    # Check if message is a cancel button
    if message.text == "❌ Отмена":
        await clear_state_preserve_admin_token(state)
        await message.answer(
            "❌ Добавление в черный список отменено.",
            reply_markup=admin_blacklist_keyboard(),
        )
        return

    # Check if message is a menu button - if so, clear state and ignore
    from bot.utils.menu_buttons import is_menu_button

    if message.text and is_menu_button(message.text):
        await clear_state_preserve_admin_token(state)
        return  # Let menu handlers process this

    identifier = message.text.strip()

    # Determine if telegram ID or wallet using validators
    telegram_id = None
    wallet_address = None

    # Try wallet address first (if it looks like one)
    if identifier.startswith("0x") and len(identifier) == 42:
        is_valid, normalized_address, error = validate_wallet_address(identifier)
        if is_valid:
            wallet_address = normalized_address.lower()
        else:
            await message.answer(
                f"❌ Неверный формат BSC адреса! {error}",
                reply_markup=cancel_keyboard(),
            )
            return
    else:
        # Try telegram ID
        is_valid, parsed_id, error = validate_telegram_id(identifier)
        if is_valid:
            telegram_id = parsed_id
        else:
            await message.answer(
                f"❌ Неверный формат! {error}\n"
                "Введите числовой Telegram ID или BSC адрес (0x...).",
                reply_markup=cancel_keyboard(),
            )
            return

    # Save to state
    await state.update_data(
        telegram_id=telegram_id,
        wallet_address=wallet_address,
    )

    await message.answer(
        "Введите причину блокировки:",
        reply_markup=cancel_keyboard(),
    )

    await state.set_state(BlacklistStates.waiting_for_reason)


@router.message(BlacklistStates.waiting_for_reason)
async def process_blacklist_reason(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Process blacklist reason."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    # Check if message is a cancel button
    if message.text == "❌ Отмена":
        await clear_state_preserve_admin_token(state)
        await message.answer(
            "❌ Добавление в черный список отменено.",
            reply_markup=admin_blacklist_keyboard(),
        )
        return

    # Check if message is a menu button - if so, clear state and ignore
    from bot.utils.menu_buttons import is_menu_button

    if message.text and is_menu_button(message.text):
        await clear_state_preserve_admin_token(state)
        return  # Let menu handlers process this

    reason = message.text.strip()

    if len(reason) < 5:
        await message.answer(
            "❌ Причина слишком короткая! Минимум 5 символов.",
            reply_markup=cancel_keyboard(),
        )
        return

    data_state = await state.get_data()
    telegram_id = data_state.get("telegram_id")
    wallet_address = data_state.get("wallet_address")

    # Get admin ID
    admin_id = None
    try:
        from app.repositories.admin_repository import AdminRepository

        admin_repo = AdminRepository(session)
        admin_obj = await admin_repo.get_by(telegram_id=message.from_user.id)
        if admin_obj:
            admin_id = admin_obj.id
    except Exception as e:
        logger.error(f"Failed to fetch admin ID for user {message.from_user.id}: {e}")

    blacklist_service = BlacklistService(session)

    try:
        entry = await blacklist_service.add_to_blacklist(
            telegram_id=telegram_id,
            wallet_address=wallet_address,
            reason=reason,
            added_by_admin_id=admin_id,
        )

        await session.commit()

        from app.models.blacklist import BlacklistActionType

        action_type_text = {
            BlacklistActionType.REGISTRATION_DENIED: "Отказ в регистрации",
            BlacklistActionType.TERMINATED: "Терминация",
            BlacklistActionType.BLOCKED: "Блокировка",
        }.get(entry.action_type, entry.action_type)

        await message.answer(
            f"✅ **Добавлено в черный список!**\n\n"
            f"ID: #{entry.id}\n"
            f"Telegram ID: {telegram_id or 'N/A'}\n"
            f"Тип: {action_type_text}\n"
            f"Причина: {reason}",
            parse_mode="Markdown",
            reply_markup=admin_blacklist_keyboard(),
        )

    except Exception as e:
        logger.error(f"Error adding to blacklist: {e}")
        await message.answer(
            f"❌ Ошибка: {e}",
            reply_markup=admin_blacklist_keyboard(),
        )

    await clear_state_preserve_admin_token(state)
