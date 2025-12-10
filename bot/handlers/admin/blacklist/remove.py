"""
Remove from blacklist handlers.

Implements the flow for removing users from the blacklist.
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
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


@router.message(F.text == "🗑️ Удалить из черного списка")
async def start_remove_from_blacklist(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Start removing from blacklist."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    await message.answer(
        "🗑️ **Удаление из черного списка**\n\n"
        "Введите Telegram ID или wallet address для удаления:",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )

    await state.set_state(BlacklistStates.waiting_for_removal_identifier)


@router.message(BlacklistStates.waiting_for_removal_identifier)
async def process_blacklist_removal(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Process blacklist removal."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    # Check if message is a cancel button
    if message.text == "❌ Отмена":
        await clear_state_preserve_admin_token(state)
        await message.answer(
            "❌ Удаление из черного списка отменено.",
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
                reply_markup=admin_blacklist_keyboard(),
            )
            await clear_state_preserve_admin_token(state)
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
                reply_markup=admin_blacklist_keyboard(),
            )
            await clear_state_preserve_admin_token(state)
            return

    blacklist_service = BlacklistService(session)

    success = await blacklist_service.remove_from_blacklist(
        telegram_id=telegram_id,
        wallet_address=wallet_address,
    )

    await session.commit()

    if success:
        await message.answer(
            "✅ **Удалено из черного списка!**\n\n"
            "Пользователь снова может использовать бота.",
            parse_mode="Markdown",
            reply_markup=admin_blacklist_keyboard(),
        )
    else:
        await message.answer(
            "❌ Запись не найдена в черном списке.",
            reply_markup=admin_blacklist_keyboard(),
        )

    await clear_state_preserve_admin_token(state)
