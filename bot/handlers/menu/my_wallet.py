"""
My Wallet handlers.

Provides comprehensive wallet information:
- Token balances (PLEX, USDT, BNB)
- Transaction history by token type
- Navigation between token transaction lists
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.wallet_info_service import WalletInfoService
from bot.keyboards.inline import InlineKeyboardBuilder
from bot.keyboards.reply import main_menu_reply_keyboard
from bot.utils.user_loader import UserLoader

router = Router()


class WalletStates(StatesGroup):
    """Wallet viewing states."""

    viewing_balances = State()
    viewing_bnb_txs = State()
    viewing_usdt_txs = State()
    viewing_plex_txs = State()


def wallet_menu_inline_keyboard():
    """Inline keyboard for wallet menu."""
    builder = InlineKeyboardBuilder()

    builder.button(text="💎 PLEX транзакции", callback_data="wallet_tx_plex")
    builder.button(text="💵 USDT транзакции", callback_data="wallet_tx_usdt")
    builder.button(text="🔶 BNB транзакции", callback_data="wallet_tx_bnb")
    builder.button(text="🔄 Обновить", callback_data="wallet_refresh")

    builder.adjust(1)
    return builder.as_markup()


def transactions_inline_keyboard(token: str):
    """Inline keyboard for transaction list."""
    builder = InlineKeyboardBuilder()

    builder.button(text="◀️ Назад к кошельку", callback_data="wallet_back")
    builder.button(text="🔄 Обновить", callback_data=f"wallet_tx_{token.lower()}")

    builder.adjust(2)
    return builder.as_markup()


def format_wallet_message(
    user: User,
    balance_data: Any,
) -> str:
    """
    Format wallet info message.

    Args:
        user: User object
        balance_data: WalletBalance from service

    Returns:
        Formatted message text
    """
    # Header
    wallet_short = f"{user.wallet_address[:8]}...{user.wallet_address[-6:]}"

    if not balance_data:
        return (
            "👛 *Мой кошелек*\n\n"
            f"📍 Адрес: `{wallet_short}`\n\n"
            "❌ Не удалось загрузить балансы.\n"
            "Попробуйте обновить позже."
        )

    text = (
        "👛 *Мой кошелек*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📍 *Адрес:*\n"
        f"`{user.wallet_address}`\n\n"
        "💰 *Балансы:*\n"
        "┌───────────────────┐\n"
        f"│ 💎 PLEX:  `{balance_data.plex_formatted}`\n"
        f"│ 💵 USDT:  `{balance_data.usdt_formatted}`\n"
        f"│ 🔶 BNB:   `{balance_data.bnb_formatted}`\n"
        "└───────────────────┘\n\n"
        f"🕐 Обновлено: {balance_data.last_updated.strftime('%H:%M:%S')}\n\n"
        "_Нажмите кнопку ниже для просмотра транзакций._"
    )

    return text


def format_transactions_message(
    token: str,
    transactions: list,
    wallet_address: str,
) -> str:
    """
    Format transaction list message.

    Args:
        token: Token symbol (PLEX, USDT, BNB)
        transactions: List of TokenTransaction
        wallet_address: User's wallet address

    Returns:
        Formatted message text
    """
    emoji_map = {"PLEX": "💎", "USDT": "💵", "BNB": "🔶"}
    emoji = emoji_map.get(token, "💰")

    wallet_short = f"{wallet_address[:8]}...{wallet_address[-6:]}"

    if not transactions:
        return (
            f"{emoji} *Транзакции {token}*\n"
            f"📍 `{wallet_short}`\n\n"
            "📭 Транзакций не найдено.\n\n"
            "_Транзакции появятся после первого_\n"
            "_перевода на этот кошелек._"
        )

    text = (
        f"{emoji} *Транзакции {token}*\n"
        f"📍 `{wallet_short}`\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    for i, tx in enumerate(transactions[:20], 1):
        # Format date
        date_str = tx.timestamp.strftime("%d.%m %H:%M")

        # Direction and amount
        if tx.direction == "in":
            direction = "📥"
            sign = "+"
        else:
            direction = "📤"
            sign = "-"

        # Format value
        value_str = tx.formatted_value

        text += (
            f"{i}. {direction} {sign}{value_str} {token}\n"
            f"   `{tx.short_hash}`\n"
            f"   📅 {date_str}\n\n"
        )

    text += (
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Показано: {len(transactions)} транзакций\n\n"
        "_Нажмите на хеш для просмотра в BSCScan._"
    )

    return text


@router.message(StateFilter('*'), F.text == "👛 Мой кошелек")
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
    logger.info(f"[WALLET] Wallet info requested by user {telegram_id}")

    user: User | None = data.get("user")
    if not user and telegram_id:
        user = await UserLoader.get_user_by_telegram_id(session, telegram_id)

    if not user:
        await message.answer(
            "⚠️ Ошибка: не удалось загрузить данные пользователя. "
            "Попробуйте отправить /start"
        )
        return

    # Check if user has wallet
    if not user.wallet_address or len(user.wallet_address) < 42:
        await message.answer(
            "❌ *Кошелек не привязан*\n\n"
            "У вас не указан BSC кошелек.\n"
            "Пожалуйста, пройдите авторизацию заново через /start",
            parse_mode="Markdown",
            reply_markup=main_menu_reply_keyboard(user=user),
        )
        return

    # Show loading
    status_msg = await message.answer("⏳ Загружаю данные кошелька...")

    try:
        # Get wallet balances
        wallet_service = WalletInfoService()
        balance_data = await wallet_service.get_wallet_balances(user.wallet_address)

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

        logger.info(f"[WALLET] Wallet info shown for user {telegram_id}")

    except Exception as e:
        logger.error(f"[WALLET] Failed to show wallet for user {telegram_id}: {e}")
        await status_msg.delete()
        await message.answer(
            "❌ Произошла ошибка при загрузке данных кошелька.\n"
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

    user: User | None = data.get("user")
    telegram_id = callback.from_user.id if callback.from_user else None

    if not user and telegram_id:
        user = await UserLoader.get_user_by_telegram_id(session, telegram_id)

    if not user or not user.wallet_address:
        await callback.answer("❌ Кошелек не найден", show_alert=True)
        return

    try:
        wallet_service = WalletInfoService()
        balance_data = await wallet_service.get_wallet_balances(user.wallet_address)

        text = format_wallet_message(user, balance_data)

        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=wallet_menu_inline_keyboard(),
        )

    except Exception as e:
        logger.error(f"[WALLET] Failed to refresh wallet: {e}")
        await callback.answer("❌ Ошибка обновления", show_alert=True)


@router.callback_query(F.data == "wallet_back")
async def back_to_wallet(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Return to wallet overview."""
    await callback.answer()

    user: User | None = data.get("user")
    telegram_id = callback.from_user.id if callback.from_user else None

    if not user and telegram_id:
        user = await UserLoader.get_user_by_telegram_id(session, telegram_id)

    if not user or not user.wallet_address:
        await callback.answer("❌ Кошелек не найден", show_alert=True)
        return

    try:
        wallet_service = WalletInfoService()
        balance_data = await wallet_service.get_wallet_balances(user.wallet_address)

        text = format_wallet_message(user, balance_data)

        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=wallet_menu_inline_keyboard(),
        )

        await state.set_state(WalletStates.viewing_balances)

    except Exception as e:
        logger.error(f"[WALLET] Failed to go back to wallet: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "wallet_tx_plex")
async def show_plex_transactions(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show PLEX transaction history."""
    await callback.answer("💎 Загружаю PLEX транзакции...")

    user: User | None = data.get("user")
    telegram_id = callback.from_user.id if callback.from_user else None

    if not user and telegram_id:
        user = await UserLoader.get_user_by_telegram_id(session, telegram_id)

    if not user or not user.wallet_address:
        await callback.answer("❌ Кошелек не найден", show_alert=True)
        return

    try:
        wallet_service = WalletInfoService()
        transactions = await wallet_service.get_plex_transactions(
            user.wallet_address, limit=20
        )

        text = format_transactions_message("PLEX", transactions, user.wallet_address)

        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=transactions_inline_keyboard("plex"),
        )

        await state.set_state(WalletStates.viewing_plex_txs)

    except Exception as e:
        logger.error(f"[WALLET] Failed to load PLEX txs: {e}")
        await callback.answer("❌ Ошибка загрузки", show_alert=True)


@router.callback_query(F.data == "wallet_tx_usdt")
async def show_usdt_transactions(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show USDT transaction history."""
    await callback.answer("💵 Загружаю USDT транзакции...")

    user: User | None = data.get("user")
    telegram_id = callback.from_user.id if callback.from_user else None

    if not user and telegram_id:
        user = await UserLoader.get_user_by_telegram_id(session, telegram_id)

    if not user or not user.wallet_address:
        await callback.answer("❌ Кошелек не найден", show_alert=True)
        return

    try:
        wallet_service = WalletInfoService()
        transactions = await wallet_service.get_usdt_transactions(
            user.wallet_address, limit=20
        )

        text = format_transactions_message("USDT", transactions, user.wallet_address)

        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=transactions_inline_keyboard("usdt"),
        )

        await state.set_state(WalletStates.viewing_usdt_txs)

    except Exception as e:
        logger.error(f"[WALLET] Failed to load USDT txs: {e}")
        await callback.answer("❌ Ошибка загрузки", show_alert=True)


@router.callback_query(F.data == "wallet_tx_bnb")
async def show_bnb_transactions(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show BNB transaction history."""
    await callback.answer("🔶 Загружаю BNB транзакции...")

    user: User | None = data.get("user")
    telegram_id = callback.from_user.id if callback.from_user else None

    if not user and telegram_id:
        user = await UserLoader.get_user_by_telegram_id(session, telegram_id)

    if not user or not user.wallet_address:
        await callback.answer("❌ Кошелек не найден", show_alert=True)
        return

    try:
        wallet_service = WalletInfoService()
        transactions = await wallet_service.get_bnb_transactions(
            user.wallet_address, limit=20
        )

        text = format_transactions_message("BNB", transactions, user.wallet_address)

        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=transactions_inline_keyboard("bnb"),
        )

        await state.set_state(WalletStates.viewing_bnb_txs)

    except Exception as e:
        logger.error(f"[WALLET] Failed to load BNB txs: {e}")
        await callback.answer("❌ Ошибка загрузки", show_alert=True)
