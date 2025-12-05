"""
Broadcast message keyboards for admin panel.

Contains keyboards for creating and sending mass messages to users.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def admin_broadcast_button_choice_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin broadcast button choice keyboard.

    Returns:
        ReplyKeyboardMarkup with button options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="✅ Добавить кнопку"),
        KeyboardButton(text="🚀 Отправить без кнопки"),
    )
    builder.row(
        KeyboardButton(text="❌ Отмена"),
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def admin_broadcast_cancel_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin broadcast cancel keyboard.

    Returns:
        ReplyKeyboardMarkup with cancel option
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="❌ Отмена"),
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def admin_broadcast_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin broadcast keyboard.

    Returns:
        ReplyKeyboardMarkup with broadcast options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="❌ Отмена"),
    )
    builder.row(
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)
