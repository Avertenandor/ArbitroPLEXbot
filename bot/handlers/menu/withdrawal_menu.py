"""
Withdrawal menu handlers.

This module contains handlers for displaying the withdrawal menu.
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.user_service import UserService
from bot.keyboards.reply import withdrawal_keyboard
from bot.utils.user_loader import UserLoader


router = Router()


@router.message(StateFilter('*'), F.text == "💸 Вывод")
async def show_withdrawal_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show withdrawal menu."""
    telegram_id = message.from_user.id if message.from_user else None
    logger.info(f"[MENU] show_withdrawal_menu called for user {telegram_id}")
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
    # Set context flag for smart number input handling in withdrawal menu
    await state.update_data(in_withdrawal_menu=True)

    user_service = UserService(session)
    balance = await user_service.get_user_balance(user.id)

    # Get min withdrawal amount
    from app.services.withdrawal_service import WithdrawalService
    withdrawal_service = WithdrawalService(session)
    min_amount = await withdrawal_service.get_min_withdrawal_amount()

    text = (
        f"💸 *Вывод средств*\n\n"
        f"Доступно для вывода: `{balance['available_balance']:.2f} USDT`\n"
        f"💰 *Минимальная сумма:* `{min_amount} USDT`\n\n"
        f"ℹ️ _Вывод возможен по накоплению {min_amount} USDT прибыли, "
        f"чтобы не нагружать выплатную систему и не переплачивать комиссии._\n\n"
        f"Выберите действие:"
    )

    logger.info(f"[MENU] Sending withdrawal menu response to user {telegram_id}")
    try:
        await message.answer(
            text, reply_markup=withdrawal_keyboard(), parse_mode="Markdown"
        )
        logger.info(f"[MENU] Withdrawal menu response sent successfully to user {telegram_id}")
    except Exception as e:
        logger.error(f"[MENU] Failed to send withdrawal menu response: {e}", exc_info=True)
        raise
