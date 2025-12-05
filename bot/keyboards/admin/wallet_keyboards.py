"""
Wallet management keyboards for admin panel.

Contains keyboards for managing crypto wallets used for deposits and withdrawals.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def admin_wallet_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin wallet management keyboard.

    Returns:
        ReplyKeyboardMarkup with wallet management options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="📊 Статус кошельков"),
    )
    builder.row(
        KeyboardButton(text="📥 Настроить кошелек для входа"),
    )
    builder.row(
        KeyboardButton(text="📤 Настроить кошелек для выдачи"),
    )
    builder.row(
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)
