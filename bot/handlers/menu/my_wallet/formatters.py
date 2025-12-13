"""
Wallet formatting utilities.

Provides functions for formatting:
- Wallet balance messages
- Transaction lists
- Inline keyboards
"""

from typing import Any

from app.models.user import User
from bot.keyboards.inline import InlineKeyboardBuilder
from bot.utils.formatters import format_wallet_short


def wallet_menu_inline_keyboard():
    """Inline keyboard for wallet menu."""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="💎 PLEX транзакции",
        callback_data="wallet_tx_plex"
    )
    builder.button(
        text="💵 USDT транзакции",
        callback_data="wallet_tx_usdt"
    )
    builder.button(
        text="🔶 BNB транзакции",
        callback_data="wallet_tx_bnb"
    )
    builder.button(text="🔄 Обновить", callback_data="wallet_refresh")

    builder.adjust(1)
    return builder.as_markup()


def transactions_inline_keyboard(token: str):
    """Inline keyboard for transaction list."""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="◀️ Назад к кошельку",
        callback_data="wallet_back"
    )
    builder.button(
        text="🔄 Обновить",
        callback_data=f"wallet_tx_{token.lower()}"
    )

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
    wallet_short = format_wallet_short(user.wallet_address)

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
        f"🕐 Обновлено: "
        f"{balance_data.last_updated.strftime('%H:%M:%S')}\n\n"
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

    wallet_short = format_wallet_short(wallet_address)

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
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
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
