"""
Blacklist management keyboards for admin panel.

Contains keyboards for managing wallet/user blacklists.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def admin_blacklist_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin blacklist management keyboard.

    Returns:
        ReplyKeyboardMarkup with blacklist management options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="➕ Добавить в blacklist"),
    )
    builder.row(
        KeyboardButton(text="🗑️ Удалить из blacklist"),
    )
    builder.row(
        KeyboardButton(text="📝 Редактировать тексты"),
    )
    builder.row(
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)
