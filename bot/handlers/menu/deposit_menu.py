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

    # Build text with statuses
    from app.config.settings import settings

    text = "💰 *Выберите уровень депозита:*\n\n"
    for level in [1, 2, 3, 4, 5]:
        if level in levels_status:
            level_info = levels_status[level]
            amount = level_info["amount"]
            status = level_info["status"]
            level_info.get("status_text", "")

            if status == "active":
                text += f"✅ Level {level}: `{amount} USDT` - Активен\n"
            elif status == "available":
                text += f"💰 Level {level}: `{amount} USDT` - Доступен\n"
            else:
                # Show reason for unavailability
                error = level_info.get("error", "")
                if "необходимо сначала купить" in error:
                    text += f"🔒 Level {level}: `{amount} USDT` - Недоступен (нет предыдущего уровня)\n"
                elif "необходимо минимум" in error:
                    text += f"🔒 Level {level}: `{amount} USDT` - Недоступен (не хватает партнёров)\n"
                else:
                    text += f"🔒 Level {level}: `{amount} USDT` - Недоступен\n"
        else:
            # Fallback
            amounts = {
                1: settings.deposit_level_1,
                2: settings.deposit_level_2,
                3: settings.deposit_level_3,
                4: settings.deposit_level_4,
                5: settings.deposit_level_5,
            }
            text += f"💰 Level {level}: `{amounts[level]:.0f} USDT`\n"

    logger.info(f"[MENU] Sending deposit menu response to user {telegram_id}")
    try:
        await message.answer(
            text, reply_markup=deposit_keyboard(levels_status=levels_status), parse_mode="Markdown"
        )
        logger.info(f"[MENU] Deposit menu response sent successfully to user {telegram_id}")
    except Exception as e:
        logger.error(f"[MENU] Failed to send deposit menu response: {e}", exc_info=True)
        raise
