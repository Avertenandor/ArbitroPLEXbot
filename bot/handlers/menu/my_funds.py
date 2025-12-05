"""
My funds handler - unified balance panel.

This module contains handlers for displaying all user balances in one view:
- System balance (available for withdrawal)
- Blockchain wallet balance (PLEX, USDT, BNB)
- PLEX payment requirements and statistics
"""

import asyncio
from decimal import Decimal
from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.blockchain_service import get_blockchain_service
from app.services.plex_payment_service import PlexPaymentService
from app.services.user_service import UserService
from bot.i18n.loader import get_translator, get_user_language
from bot.keyboards.reply import main_menu_reply_keyboard
from bot.utils.user_loader import UserLoader

router = Router()


def format_balance(value: Decimal | None, decimals: int = 4) -> str:
    """Format balance with specified decimals."""
    if value is None:
        return "—"
    return f"{float(value):,.{decimals}f}"


def calculate_days_remaining(plex_balance: Decimal | None, daily_plex: Decimal) -> str:
    """
    Calculate how many days the PLEX balance will last.

    Args:
        plex_balance: Current PLEX balance
        daily_plex: Daily PLEX consumption

    Returns:
        Formatted string with days count
    """
    if plex_balance is None or daily_plex <= 0:
        return "—"

    days = float(plex_balance) / float(daily_plex)

    if days >= 365:
        return "∞ (более года)"

    return f"{int(days)}"


@router.message(StateFilter('*'), F.text == "💰 Мои средства")
async def show_my_funds(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Show unified funds panel with all balances.

    Displays:
    - System balance (available for withdrawal)
    - Blockchain wallet balance (PLEX, USDT, BNB)
    - PLEX payment statistics (daily consumption, days remaining)
    """
    telegram_id = message.from_user.id if message.from_user else None
    logger.info(f"[MY_FUNDS] show_my_funds called for user {telegram_id}")

    user: User | None = data.get("user")
    if not user and telegram_id:
        user = await UserLoader.get_user_by_telegram_id(session, telegram_id)

    if not user:
        from bot.i18n.loader import get_text
        await message.answer(get_text('errors.user_load_error'))
        return

    await state.clear()

    # Get user language for i18n
    user_language = await get_user_language(session, user.id)
    _ = get_translator(user_language)

    # Get wallet address
    wallet_address = user.wallet_address
    if not wallet_address:
        await message.answer(
            "❌ *Кошелек не найден*\n\n"
            "У вас не указан адрес кошелька. "
            "Пожалуйста, пройдите регистрацию заново через /start",
            parse_mode="Markdown"
        )
        return

    # Send "loading" message
    loading_msg = await message.answer(
        "⏳ *Загружаю данные...*\n\n"
        "Подождите, идет получение информации...",
        parse_mode="Markdown"
    )

    try:
        # Initialize services
        user_service = UserService(session)
        plex_service = PlexPaymentService(session)
        blockchain_service = get_blockchain_service()

        # Fetch all data in parallel for better performance
        async def safe_get_system_balance():
            try:
                return await user_service.get_user_balance(user.id)
            except Exception as e:
                logger.error(f"[MY_FUNDS] Error getting system balance: {e}")
                return None

        async def safe_get_plex_payment_status():
            try:
                return await plex_service.get_user_payment_status(user.id)
            except Exception as e:
                logger.error(f"[MY_FUNDS] Error getting PLEX payment status: {e}")
                return None

        async def safe_get_plex_balance():
            try:
                return await blockchain_service.get_plex_balance(wallet_address)
            except Exception as e:
                logger.error(f"[MY_FUNDS] Error getting PLEX balance: {e}")
                return None

        async def safe_get_usdt_balance():
            try:
                return await blockchain_service.get_usdt_balance(wallet_address)
            except Exception as e:
                logger.error(f"[MY_FUNDS] Error getting USDT balance: {e}")
                return None

        async def safe_get_bnb_balance():
            try:
                return await blockchain_service.get_native_balance(wallet_address)
            except Exception as e:
                logger.error(f"[MY_FUNDS] Error getting BNB balance: {e}")
                return None

        # Execute all queries in parallel
        (
            system_balance,
            plex_status,
            plex_balance,
            usdt_balance,
            bnb_balance,
        ) = await asyncio.gather(
            safe_get_system_balance(),
            safe_get_plex_payment_status(),
            safe_get_plex_balance(),
            safe_get_usdt_balance(),
            safe_get_bnb_balance(),
        )

        logger.info(
            f"[MY_FUNDS] Data loaded for {telegram_id}: "
            f"system={system_balance is not None}, "
            f"plex_status={plex_status is not None}, "
            f"PLEX={plex_balance}, USDT={usdt_balance}, BNB={bnb_balance}"
        )

        # Extract system balance data
        available_balance = Decimal("0")
        if system_balance:
            available_balance = system_balance.get('available_balance', Decimal("0"))

        # Extract PLEX payment data
        daily_plex = Decimal("0")
        if plex_status:
            daily_plex = plex_status.get('total_daily_plex', Decimal("0"))

        # Calculate days remaining
        days_remaining = calculate_days_remaining(plex_balance, daily_plex)

        # Format balances for display
        system_display = format_balance(available_balance, 2)
        plex_display = format_balance(plex_balance, 2)
        usdt_display = format_balance(usdt_balance, 2)
        bnb_display = format_balance(bnb_balance, 6)
        daily_plex_display = format_balance(daily_plex, 2)

        # Build response message
        text = (
            "💰 *МОИ СРЕДСТВА*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 *В системе:* `{system_display}` USDT\n"
            "   _(доступно для вывода)_\n\n"
            "🔗 *На кошельке BSC:*\n"
            f"   • PLEX: `{plex_display}` монет\n"
            f"   • USDT: `{usdt_display}` USDT\n"
            f"   • BNB: `{bnb_display}` BNB\n\n"
        )

        # Add PLEX statistics if there are active deposits
        if daily_plex > 0:
            text += (
                "⚡ *Работа системы:*\n"
                f"   Расход PLEX: `{daily_plex_display}`/день\n"
                f"   Хватит на: ~`{days_remaining}` дней\n\n"
            )

        text += (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "_Балансы получены из блокчейна BSC_"
        )

        # Delete loading message and send result
        try:
            await loading_msg.delete()
        except Exception:
            pass

        # Get keyboard from main menu (to return user to menu)
        from app.repositories.blacklist_repository import BlacklistRepository
        blacklist_repo = BlacklistRepository(session)
        blacklist_entry = await blacklist_repo.find_by_telegram_id(user.telegram_id)
        is_admin = data.get("is_admin", False)

        keyboard = main_menu_reply_keyboard(
            user=user,
            blacklist_entry=blacklist_entry,
            is_admin=is_admin
        )

        await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)

        logger.info(
            f"[MY_FUNDS] Successfully displayed funds for user {telegram_id}: "
            f"system={system_display}, PLEX={plex_display}, "
            f"USDT={usdt_display}, BNB={bnb_display}, daily_plex={daily_plex_display}"
        )

    except Exception as e:
        logger.error(f"[MY_FUNDS] Error fetching funds for {telegram_id}: {e}")

        # Delete loading message
        try:
            await loading_msg.delete()
        except Exception:
            pass

        # Show error
        text = (
            "⚠️ *Ошибка получения данных*\n\n"
            "Не удалось получить информацию о средствах.\n"
            "Попробуйте позже."
        )

        await message.answer(text, parse_mode="Markdown")
