"""
Base wallet handlers.

Provides wallet overview and navigation:
- Show wallet balances
- Refresh wallet data
- Return to wallet overview
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.wallet_info_service import WalletInfoService
from bot.keyboards.reply import main_menu_reply_keyboard
from bot.utils.user_context import get_user_from_context

from .formatters import (
    format_wallet_message,
    wallet_menu_inline_keyboard,
)
from .states import WalletStates


router = Router()


@router.message(StateFilter("*"), F.text == "👛 Мой кошелек")
async def show_my_wallet(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Show user's wallet information with balances.

    Displays:
    - Wallet address
    - PLEX, USDT, BNB balances
    - Buttons to view transaction history
    """
    telegram_id = message.from_user.id if message.from_user else None
    logger.info(
        f"[WALLET] Wallet info requested by user {telegram_id}"
    )

    user = await get_user_from_context(message, session, data)
    if not user:
        await message.answer(
            "⚠️ Ошибка: не удалось загрузить "
            "данные пользователя. "
            "Попробуйте отправить /start"
        )
        return

    # Check if user has wallet
    if not user.wallet_address or len(user.wallet_address) < 42:
        await message.answer(
            "❌ *Кошелек не привязан*\n\n"
            "У вас не указан BSC кошелек.\n"
            "Пожалуйста, пройдите авторизацию заново "
            "через /start",
            parse_mode="Markdown",
            reply_markup=main_menu_reply_keyboard(user=user),
        )
        return

    # Show loading
    status_msg = await message.answer(
        "⏳ Загружаю данные кошелька..."
    )

    try:
        # Get wallet balances
        wallet_service = WalletInfoService()
        balance_data = await wallet_service.get_wallet_balances(
            user.wallet_address
        )

        # Format message
        text = format_wallet_message(user, balance_data)

        # Delete loading and send result
        await status_msg.delete()
        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=wallet_menu_inline_keyboard(),
        )

        # Set state for navigation
        await state.set_state(WalletStates.viewing_balances)
        await state.update_data(wallet_address=user.wallet_address)

        logger.info(
            f"[WALLET] Wallet info shown for user {telegram_id}"
        )

    except Exception as e:
        logger.error(
            f"[WALLET] Failed to show wallet "
            f"for user {telegram_id}: {e}"
        )
        await status_msg.delete()
        await message.answer(
            "❌ Произошла ошибка при загрузке "
            "данных кошелька.\n"
            "Попробуйте позже.",
            reply_markup=main_menu_reply_keyboard(user=user),
        )


@router.callback_query(F.data == "wallet_refresh")
async def refresh_wallet(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Refresh wallet balances."""
    await callback.answer("🔄 Обновляю...")

    user = await get_user_from_context(callback, session, data)
    if not user or not user.wallet_address:
        await callback.answer(
            "❌ Кошелек не найден",
            show_alert=True
        )
        return

    try:
        wallet_service = WalletInfoService()
        balance_data = await wallet_service.get_wallet_balances(
            user.wallet_address
        )

        text = format_wallet_message(user, balance_data)

        # Prefer editing the current message,
        # but fall back to sending a new one
        # if Telegram disallows editing
        # (e.g., message too old / already deleted).
        if callback.message:
            try:
                await callback.message.edit_text(
                    text,
                    parse_mode="Markdown",
                    reply_markup=wallet_menu_inline_keyboard(),
                )
            except Exception as edit_error:
                logger.warning(
                    f"[WALLET] edit_text failed on refresh, "
                    f"sending new message: {edit_error}"
                )
                await callback.message.answer(
                    text,
                    parse_mode="Markdown",
                    reply_markup=wallet_menu_inline_keyboard(),
                )
        else:
            await callback.answer(
                "❌ Не удалось обновить: сообщение не найдено",
                show_alert=True
            )
            return

    except Exception as e:
        logger.error(f"[WALLET] Failed to refresh wallet: {e}")
        await callback.answer(
            "❌ Ошибка обновления",
            show_alert=True
        )


@router.callback_query(F.data == "wallet_back")
async def back_to_wallet(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Return to wallet overview."""
    await callback.answer()

    user = await get_user_from_context(callback, session, data)
    if not user or not user.wallet_address:
        await callback.answer(
            "❌ Кошелек не найден",
            show_alert=True
        )
        return

    try:
        wallet_service = WalletInfoService()
        balance_data = await wallet_service.get_wallet_balances(
            user.wallet_address
        )

        text = format_wallet_message(user, balance_data)

        if callback.message:
            try:
                await callback.message.edit_text(
                    text,
                    parse_mode="Markdown",
                    reply_markup=wallet_menu_inline_keyboard(),
                )
            except Exception as edit_error:
                logger.warning(
                    f"[WALLET] edit_text failed on back, "
                    f"sending new message: {edit_error}"
                )
                await callback.message.answer(
                    text,
                    parse_mode="Markdown",
                    reply_markup=wallet_menu_inline_keyboard(),
                )
        else:
            await callback.answer(
                "❌ Не удалось открыть кошелек",
                show_alert=True
            )
            return

        await state.set_state(WalletStates.viewing_balances)

    except Exception as e:
        logger.error(
            f"[WALLET] Failed to go back to wallet: {e}"
        )
        await callback.answer("❌ Ошибка", show_alert=True)
