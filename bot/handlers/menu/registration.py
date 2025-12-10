"""
Registration menu handlers.

This module contains handlers for starting the registration process from the menu.
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.blacklist_repository import BlacklistRepository
from bot.keyboards.reply import main_menu_reply_keyboard
from bot.states.registration import RegistrationStates


router = Router()


@router.message(StateFilter('*'), F.text == "📝 Регистрация")
async def start_registration(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Start registration process from menu button.

    Args:
        message: Telegram message
        session: Database session
        state: FSM state
        **data: Handler data
    """
    user: User | None = data.get("user")

    # If user already registered, show main menu
    if user:
        logger.info(
            f"start_registration: User {user.telegram_id} already registered, "
            "showing main menu"
        )
        is_admin = data.get("is_admin", False)
        blacklist_repo = BlacklistRepository(session)
        blacklist_entry = await blacklist_repo.find_by_telegram_id(user.telegram_id)
        await message.answer(
            "✅ Вы уже зарегистрированы!",
            reply_markup=main_menu_reply_keyboard(
                user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
            ),
        )
        await state.clear()
        return

    # Clear any active FSM state
    await state.clear()

    # Show registration welcome message
    welcome_text = (
        "👋 **Добро пожаловать в ArbitroPLEXbot!**\n\n"
        "ArbitroPLEXbot — это платформа для инвестиций в USDT на сети "
        "Binance Smart Chain (BEP-20).\n\n"
        "**Важно:**\n"
        "• Работа ведется только с сетью **BSC (BEP-20)**\n"
        "• Базовая валюта депозитов — **USDT BEP-20**\n"
        "• **Требование:** Для доступа нужен активный кролик от [DEXRabbit](https://xn--80apagbbfxgmuj4j.site/)\n\n"
        "🌐 **Официальный сайт:**\n"
        "[arbitrage-bot.com](https://arbitrage-bot.com/)\n\n"
        "Для начала работы необходимо пройти регистрацию.\n\n"
        "📝 **Шаг 1:** Введите ваш BSC (BEP-20) адрес кошелька\n"
        "Формат: `0x...` (42 символа)\n\n"
        "⚠️ **КРИТИЧНО:** Указывайте только **ЛИЧНЫЙ** кошелек (Trust Wallet, MetaMask, SafePal или любой холодный кошелек).\n"
        "🚫 **НЕ указывайте** адрес биржи (Binance, Bybit), иначе выплаты могут быть утеряны!"
    )

    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        disable_web_page_preview=False,
        reply_markup=ReplyKeyboardRemove(),
    )

    # Start registration FSM
    await state.set_state(RegistrationStates.waiting_for_wallet)
