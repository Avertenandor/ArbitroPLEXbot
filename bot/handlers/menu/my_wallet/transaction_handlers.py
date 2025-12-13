"""
Transaction history handlers.

Provides transaction viewing by token type:
- PLEX transactions
- USDT transactions
- BNB transactions
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.wallet_info_service import WalletInfoService
from bot.utils.user_context import get_user_from_context

from .formatters import (
    format_transactions_message,
    transactions_inline_keyboard,
)
from .states import WalletStates


router = Router()


@router.callback_query(F.data == "wallet_tx_plex")
async def show_plex_transactions(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show PLEX transaction history."""
    await callback.answer("💎 Загружаю PLEX транзакции...")

    user = await get_user_from_context(callback, session, data)
    if not user or not user.wallet_address:
        await callback.answer(
            "❌ Кошелек не найден",
            show_alert=True
        )
        return

    try:
        wallet_service = WalletInfoService()
        transactions = await wallet_service.get_plex_transactions(
            user.wallet_address,
            limit=20
        )

        text = format_transactions_message(
            "PLEX",
            transactions,
            user.wallet_address
        )

        if callback.message:
            try:
                await callback.message.edit_text(
                    text,
                    parse_mode="Markdown",
                    reply_markup=transactions_inline_keyboard("plex"),
                )
            except Exception as edit_error:
                logger.warning(
                    f"[WALLET] edit_text failed on plex txs, "
                    f"sending new message: {edit_error}"
                )
                await callback.message.answer(
                    text,
                    parse_mode="Markdown",
                    reply_markup=transactions_inline_keyboard("plex"),
                )
        else:
            await callback.answer(
                "❌ Не удалось показать транзакции",
                show_alert=True
            )
            return

        await state.set_state(WalletStates.viewing_plex_txs)

    except Exception as e:
        logger.error(f"[WALLET] Failed to load PLEX txs: {e}")
        await callback.answer(
            "❌ Ошибка загрузки",
            show_alert=True
        )


@router.callback_query(F.data == "wallet_tx_usdt")
async def show_usdt_transactions(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show USDT transaction history."""
    await callback.answer("💵 Загружаю USDT транзакции...")

    user = await get_user_from_context(callback, session, data)
    if not user or not user.wallet_address:
        await callback.answer(
            "❌ Кошелек не найден",
            show_alert=True
        )
        return

    try:
        wallet_service = WalletInfoService()
        transactions = await wallet_service.get_usdt_transactions(
            user.wallet_address,
            limit=20
        )

        text = format_transactions_message(
            "USDT",
            transactions,
            user.wallet_address
        )

        if callback.message:
            try:
                await callback.message.edit_text(
                    text,
                    parse_mode="Markdown",
                    reply_markup=transactions_inline_keyboard("usdt"),
                )
            except Exception as edit_error:
                logger.warning(
                    f"[WALLET] edit_text failed on usdt txs, "
                    f"sending new message: {edit_error}"
                )
                await callback.message.answer(
                    text,
                    parse_mode="Markdown",
                    reply_markup=transactions_inline_keyboard("usdt"),
                )
        else:
            await callback.answer(
                "❌ Не удалось показать транзакции",
                show_alert=True
            )
            return

        await state.set_state(WalletStates.viewing_usdt_txs)

    except Exception as e:
        logger.error(f"[WALLET] Failed to load USDT txs: {e}")
        await callback.answer(
            "❌ Ошибка загрузки",
            show_alert=True
        )


@router.callback_query(F.data == "wallet_tx_bnb")
async def show_bnb_transactions(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show BNB transaction history."""
    await callback.answer("🔶 Загружаю BNB транзакции...")

    user = await get_user_from_context(callback, session, data)
    if not user or not user.wallet_address:
        await callback.answer(
            "❌ Кошелек не найден",
            show_alert=True
        )
        return

    try:
        wallet_service = WalletInfoService()
        transactions = await wallet_service.get_bnb_transactions(
            user.wallet_address,
            limit=20
        )

        text = format_transactions_message(
            "BNB",
            transactions,
            user.wallet_address
        )

        if callback.message:
            try:
                await callback.message.edit_text(
                    text,
                    parse_mode="Markdown",
                    reply_markup=transactions_inline_keyboard("bnb"),
                )
            except Exception as edit_error:
                logger.warning(
                    f"[WALLET] edit_text failed on bnb txs, "
                    f"sending new message: {edit_error}"
                )
                await callback.message.answer(
                    text,
                    parse_mode="Markdown",
                    reply_markup=transactions_inline_keyboard("bnb"),
                )
        else:
            await callback.answer(
                "❌ Не удалось показать транзакции",
                show_alert=True
            )
            return

        await state.set_state(WalletStates.viewing_bnb_txs)

    except Exception as e:
        logger.error(f"[WALLET] Failed to load BNB txs: {e}")
        await callback.answer(
            "❌ Ошибка загрузки",
            show_alert=True
        )
