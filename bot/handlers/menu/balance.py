"""
Balance menu handlers.

This module contains handlers for displaying user balance information.
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
from bot.i18n.loader import get_translator, get_user_language
from bot.keyboards.user.menus import balance_menu_keyboard
from bot.utils.formatters import format_balance
from bot.utils.user_context import get_user_from_context


router = Router()


@router.message(StateFilter('*'), F.text == "📊 Баланс")
async def show_balance(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show user balance."""
    telegram_id = message.from_user.id if message.from_user else None
    logger.info(f"[MENU] show_balance called for user {telegram_id}")

    user = await get_user_from_context(message, session, data)
    logger.info(f"[MENU] User from context: {user.id if user else None}, data keys: {list(data.keys())}")
    if not user:
        # R13-3: Get default language for error message
        from bot.i18n.loader import get_text
        await message.answer(get_text('errors.user_load_error'))
        return
    await state.clear()

    user_service = UserService(session)
    balance = await user_service.get_user_balance(user.id)

    # R13-3: Get user language for i18n
    user_language = await get_user_language(session, user.id)
    _ = get_translator(user_language)

    if not balance:
        await message.answer(_('errors.balance_error'))
        return

    # Get bonus info
    bonus_balance = balance.get('bonus_balance', 0) or 0
    bonus_roi = balance.get('bonus_roi_earned', 0) or 0

    text = (
        f"💰 *Ваш баланс:*\n\n"
        f"Общий: `{format_balance(balance['total_balance'], decimals=2)} USDT`\n"
        f"Доступно: `{format_balance(balance['available_balance'], decimals=2)} USDT`\n"
        f"В ожидании: `{format_balance(balance['pending_earnings'], decimals=2)} USDT`\n"
    )

    # Add bonus section if user has bonuses
    if bonus_balance > 0 or bonus_roi > 0:
        text += (
            f"\n🎁 *Бонусы:*\n"
            f"Бонусный баланс: `{format_balance(bonus_balance, decimals=2)} USDT`\n"
            f"Заработано с бонусов: `{format_balance(bonus_roi, decimals=2)} USDT`\n"
        )

    text += (
        f"\n📊 *Статистика:*\n"
        f"Депозиты: `{format_balance(balance['total_deposits'], decimals=2)} USDT`\n"
        f"Выводы: `{format_balance(balance['total_withdrawals'], decimals=2)} USDT`\n"
        f"Заработано: `{format_balance(balance['total_earnings'], decimals=2)} USDT`"
    )

    await message.answer(text, parse_mode="Markdown", reply_markup=balance_menu_keyboard())
