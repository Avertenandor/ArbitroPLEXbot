"""
User cabinet submenu handlers.

This module contains handlers for the user cabinet submenu, which includes:
- Active deposits view
- Transaction history
- Calculator
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from bot.keyboards.user import cabinet_submenu_keyboard
from bot.utils.user_context import get_user_from_context


router = Router()


@router.message(StateFilter('*'), F.text == "📊 Мой кабинет")
async def show_cabinet_submenu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Show user cabinet submenu.

    Args:
        message: Message object
        session: Database session
        state: FSM state
        **data: Handler data (includes user from AuthMiddleware)
    """
    telegram_id = message.from_user.id if message.from_user else None
    logger.info(f"[SUBMENU] Cabinet submenu requested by user {telegram_id}")

    user = await get_user_from_context(message, session, data)
    if not user:
        await message.answer(
            "⚠️ Ошибка: не удалось загрузить данные пользователя. "
            "Попробуйте отправить /start"
        )
        return

    await state.clear()

    text = (
        "📊 *Мой кабинет*\n\n"
        "В личном кабинете вы можете:\n\n"
        "📦 *Мои депозиты* — просмотр активных депозитов\n"
        "📜 *История операций* — полная история транзакций\n"
        "📊 *Калькулятор* — расчет потенциального дохода\n\n"
        "Выберите нужный раздел:"
    )

    await message.answer(
        text,
        reply_markup=cabinet_submenu_keyboard(),
        parse_mode="Markdown"
    )
    logger.info(f"[SUBMENU] Cabinet submenu shown to user {telegram_id}")
