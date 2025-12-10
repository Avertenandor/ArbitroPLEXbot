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
from bot.utils.user_loader import UserLoader


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
    user: User | None = data.get("user")
    logger.info(f"[MENU] User from data: {user.id if user else None}, data keys: {list(data.keys())}")
    if not user and telegram_id:
        user = await UserLoader.get_user_by_telegram_id(session, telegram_id)
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
        f"Общий: `{balance['total_balance']:.2f} USDT`\n"
        f"Доступно: `{balance['available_balance']:.2f} USDT`\n"
        f"В ожидании: `{balance['pending_earnings']:.2f} USDT`\n"
    )

    # Add bonus section if user has bonuses
    if bonus_balance > 0 or bonus_roi > 0:
        text += (
            f"\n🎁 *Бонусы:*\n"
            f"Бонусный баланс: `{float(bonus_balance):.2f} USDT`\n"
            f"Заработано с бонусов: `{float(bonus_roi):.2f} USDT`\n"
        )

    text += (
        f"\n📊 *Статистика:*\n"
        f"Депозиты: `{balance['total_deposits']:.2f} USDT`\n"
        f"Выводы: `{balance['total_withdrawals']:.2f} USDT`\n"
        f"Заработано: `{balance['total_earnings']:.2f} USDT`"
    )

    await message.answer(text, parse_mode="Markdown", reply_markup=balance_menu_keyboard())
