"""
Wallet balance handlers.

This module contains handlers for displaying user's blockchain wallet balance.
Shows PLEX, USDT, and BNB balances by scanning the blockchain.
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
from bot.i18n.loader import get_translator, get_user_language
from bot.utils.user_loader import UserLoader

router = Router()


def format_balance(value: Decimal | None, decimals: int = 4) -> str:
    """Format balance with specified decimals."""
    if value is None:
        return "—"
    return f"{float(value):,.{decimals}f}"


def format_wallet_for_copy(address: str) -> str:
    """Format wallet address for display with full address for copying."""
    return f"`{address}`"


def format_wallet_short(address: str) -> str:
    """Format wallet address shortened for display."""
    if len(address) > 20:
        return f"{address[:10]}...{address[-8:]}"
    return address


@router.message(StateFilter('*'), F.text == "💰 Баланс кошелька")
async def show_wallet_balance(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Show user's blockchain wallet balance.

    Scans the blockchain and displays:
    - PLEX token balance
    - USDT token balance
    - BNB (native) balance
    - Wallet address for copying
    """
    telegram_id = message.from_user.id if message.from_user else None
    logger.info(f"[WALLET_BALANCE] show_wallet_balance called for user {telegram_id}")

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

    # Send "scanning" message
    scanning_msg = await message.answer(
        "⏳ *Сканирую баланс кошелька...*\n\n"
        "Подождите, идет проверка блокчейна...",
        parse_mode="Markdown"
    )

    try:
        # Get blockchain service and PLEX payment service
        blockchain_service = get_blockchain_service()
        plex_service = PlexPaymentService(session)

        # Fetch all balances in parallel for better performance
        async def safe_get_plex():
            try:
                return await blockchain_service.get_plex_balance(wallet_address)
            except Exception as e:
                logger.error(f"[WALLET_BALANCE] Error getting PLEX balance: {e}")
                return None

        async def safe_get_usdt():
            try:
                return await blockchain_service.get_usdt_balance(wallet_address)
            except Exception as e:
                logger.error(f"[WALLET_BALANCE] Error getting USDT balance: {e}")
                return None

        async def safe_get_bnb():
            try:
                return await blockchain_service.get_native_balance(wallet_address)
            except Exception as e:
                logger.error(f"[WALLET_BALANCE] Error getting BNB balance: {e}")
                return None

        async def safe_get_forecast():
            try:
                return await plex_service.calculate_plex_forecast(user.id)
            except Exception as e:
                logger.error(f"[WALLET_BALANCE] Error getting PLEX forecast: {e}")
                return None

        # Execute all balance queries and forecast in parallel
        plex_balance, usdt_balance, bnb_balance, forecast = await asyncio.gather(
            safe_get_plex(),
            safe_get_usdt(),
            safe_get_bnb(),
            safe_get_forecast(),
        )

        logger.info(
            f"[WALLET_BALANCE] Balances for {telegram_id}: "
            f"PLEX={plex_balance}, USDT={usdt_balance}, BNB={bnb_balance}"
        )

        # Format balances for display
        plex_display = format_balance(plex_balance, 2)
        usdt_display = format_balance(usdt_balance, 2)
        bnb_display = format_balance(bnb_balance, 6)

        # Build response message
        text = (
            "💰 *Баланс вашего кошелька*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🟣 *PLEX:* `{plex_display}` PLEX\n"
            f"💵 *USDT:* `{usdt_display}` USDT\n"
            f"🟡 *BNB:* `{bnb_display}` BNB\n\n"
        )

        # Add PLEX forecast if available
        if forecast and not forecast.get("error"):
            daily_plex = forecast["daily_plex"]
            days_left = forecast["days_left"]
            warning = forecast["warning"]
            active_deposits_sum = forecast["active_deposits_sum"]

            # Only show forecast if user has active deposits
            if daily_plex > 0:
                text += "━━━━━━━━━━━━━━━━━━━━━━\n"
                text += "📊 *Прогноз расхода PLEX*\n\n"
                text += f"📌 Активные депозиты: `{float(active_deposits_sum):,.2f}` USD\n"
                text += f"⚡️ Дневной расход: `{float(daily_plex):,.0f}` PLEX/день\n"

                # Format days left display
                if days_left == float('inf'):
                    days_display = "∞"
                elif days_left >= 365:
                    days_display = f"{days_left/365:.1f} лет"
                elif days_left >= 30:
                    days_display = f"{days_left/30:.1f} месяцев"
                else:
                    days_display = f"{days_left:.1f} дней"

                text += f"⏰ Хватит на: `{days_display}`\n\n"

                # Add warning if critically low
                if warning:
                    text += "⚠️ *ВНИМАНИЕ!* Баланс PLEX заканчивается!\n"
                    text += "Пополните баланс для продолжения работы.\n\n"

        text += (
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📋 *Ваш кошелек (нажмите для копирования):*\n"
            f"`{wallet_address}`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"_Адрес: {format_wallet_short(wallet_address)}_\n\n"
            "💡 _Баланс получен из блокчейна BSC_"
        )

        # Delete scanning message and send result
        try:
            await scanning_msg.delete()
        except Exception:
            pass

        await message.answer(text, parse_mode="Markdown")

        logger.info(
            f"[WALLET_BALANCE] Successfully displayed balance for user {telegram_id}: "
            f"PLEX={plex_balance}, USDT={usdt_balance}, BNB={bnb_balance}"
        )

    except Exception as e:
        logger.error(f"[WALLET_BALANCE] Error fetching wallet balance for {telegram_id}: {e}")

        # Delete scanning message
        try:
            await scanning_msg.delete()
        except Exception:
            pass

        # Show error with partial info
        text = (
            "⚠️ *Ошибка получения баланса*\n\n"
            "Не удалось получить баланс из блокчейна.\n"
            "Попробуйте позже.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📋 *Ваш кошелек (нажмите для копирования):*\n"
            f"`{wallet_address}`\n\n"
            f"_Адрес: {format_wallet_short(wallet_address)}_"
        )

        await message.answer(text, parse_mode="Markdown")
