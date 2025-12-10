"""
Deposit menu handlers.

This module contains handlers for displaying the deposit menu with level statuses.
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from bot.keyboards.reply import deposit_keyboard
from bot.utils.user_loader import UserLoader


router = Router()


@router.message(StateFilter('*'), F.text == "💰 Депозит")
async def show_deposit_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show deposit menu."""
    telegram_id = message.from_user.id if message.from_user else None
    logger.info(f"[MENU] show_deposit_menu called for user {telegram_id}")
    user: User | None = data.get("user")
    logger.info(f"[MENU] User from data: {user.id if user else None}, data keys: {list(data.keys())}")
    if not user and telegram_id:
        user = await UserLoader.get_user_by_telegram_id(session, telegram_id)
    if not user:
        await message.answer(
            "⚠️ Ошибка: не удалось загрузить данные пользователя. "
            "Попробуйте отправить /start"
        )
        return

    await state.clear()

    # Get level statuses using DepositValidationService
    from app.services.deposit_validation_service import (
        DepositValidationService,
    )

    validation_service = DepositValidationService(session)
    levels_status = await validation_service.get_available_levels(user.id)

    # Build text with statuses and corridors
    text = "💰 *Выберите уровень депозита:*\n\n"
    text += "_Депозиты открываются последовательно, начиная с тестового._\n\n"

    # All levels including test (0)
    for level in [0, 1, 2, 3, 4, 5]:
        if level in levels_status:
            level_info = levels_status[level]
            min_amt = level_info.get("min_amount", 0)
            max_amt = level_info.get("max_amount", 0)
            status = level_info["status"]
            display_name = level_info.get("display_name", f"Level {level}")
            corridor = f"${int(min_amt)}-${int(max_amt)}"

            if status == "active":
                text += f"✅ {display_name}: `{corridor}` - Активен\n"
            elif status == "available":
                text += f"💰 {display_name}: `{corridor}` - Доступен\n"
            else:
                # Show reason for unavailability
                error = level_info.get("error", "")
                if "необходимо сначала" in error.lower() or "предыдущ" in error.lower():
                    text += f"🔒 {display_name}: `{corridor}` - Нужен предыдущий уровень\n"
                elif "уже приобретен" in error.lower():
                    text += f"✅ {display_name}: `{corridor}` - Уже куплен\n"
                else:
                    text += f"🔒 {display_name}: `{corridor}`\n"

    text += "\n_📋 Правило PLEX: 10 монет за каждый $1 депозита ежедневно._"

    logger.info(f"[MENU] Sending deposit menu response to user {telegram_id}")
    try:
        await message.answer(
            text, reply_markup=deposit_keyboard(levels_status=levels_status), parse_mode="Markdown"
        )
        logger.info(f"[MENU] Deposit menu response sent successfully to user {telegram_id}")
    except Exception as e:
        logger.error(f"[MENU] Failed to send deposit menu response: {e}", exc_info=True)
        raise
