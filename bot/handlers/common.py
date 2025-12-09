"""
Common handlers for all states.

This module contains universal handlers that work across all FSM states.
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from bot.keyboards.reply import main_menu_reply_keyboard

router = Router(name="common")


@router.message(F.text == "❌ Отмена")
async def cancel_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User | None = None,
    **data: Any,
) -> None:
    """
    Universal cancel handler for any FSM state.

    This handler catches the "❌ Отмена" button from any state
    and clears the state, returning to the main menu.
    
    NOTE: Admin-specific states (BonusStates, etc.) have their own
    cancel handlers that should take priority.

    Args:
        message: Telegram message
        state: FSM state
        session: Database session
        user: Current user (optional)
        **data: Additional handler data
    """
    current_state = await state.get_state()

    if current_state:
        # Skip if this is an admin-specific state (let admin handlers handle it)
        admin_state_prefixes = (
            "BonusStates:",
            "BonusMgmtStates:",
            "AdminUserStates:",
            "UserEditStates:",
        )
        if current_state.startswith(admin_state_prefixes):
            logger.debug(
                f"Common cancel_handler skipping admin state: {current_state}"
            )
            return  # Let admin-specific handlers process this
        
        logger.info(
            f"User {user.id if user else 'unknown'} cancelled operation from state: {current_state}"
        )
        await state.clear()

        # Get blacklist info for proper menu
        blacklist_entry = None
        if user:
            try:
                from app.repositories.blacklist_repository import BlacklistRepository
                blacklist_repo = BlacklistRepository(session)
                blacklist_entry = await blacklist_repo.find_by_telegram_id(user.telegram_id)
            except Exception as e:
                logger.error(f"Error fetching blacklist entry in cancel handler: {e}")

        is_admin = data.get("is_admin", False)

        await message.answer(
            "Операция отменена.",
            reply_markup=main_menu_reply_keyboard(
                user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
            ) if user else None,
        )
    else:
        # No active state, just acknowledge
        await message.answer("Нет активных операций для отмены.")
