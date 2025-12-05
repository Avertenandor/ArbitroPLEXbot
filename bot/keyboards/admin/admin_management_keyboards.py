"""
Admin management keyboards for admin panel.

Contains keyboards for managing other admins (super admin only feature).
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def admin_management_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin management keyboard (for managing admins).

    Returns:
        ReplyKeyboardMarkup with admin management options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="➕ Добавить админа"),
    )
    builder.row(
        KeyboardButton(text="📋 Список админов"),
    )
    builder.row(
        KeyboardButton(text="🗑️ Удалить админа"),
    )
    builder.row(
        KeyboardButton(text="🛑 Экстренно заблокировать админа"),
    )
    builder.row(
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)
