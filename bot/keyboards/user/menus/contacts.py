"""
Contact management keyboards module.

This module contains keyboards related to contact management:
- Contact update menu
- Contact input keyboard
- Contacts choice keyboard
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def contact_update_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Contact update menu keyboard.

    Returns:
        ReplyKeyboardMarkup with contact update options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="📞 Обновить телефон"),
    )
    builder.row(
        KeyboardButton(text="📧 Обновить email"),
    )
    builder.row(
        KeyboardButton(text="📝 Обновить оба"),
    )
    builder.row(
        KeyboardButton(text="◀️ Назад"),
        KeyboardButton(text="🏠 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def contact_input_keyboard() -> ReplyKeyboardMarkup:
    """
    Contact input keyboard with skip option.

    Returns:
        ReplyKeyboardMarkup with skip and navigation options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="⏭ Пропустить"),
    )
    builder.row(
        KeyboardButton(text="◀️ Назад"),
        KeyboardButton(text="🏠 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def contacts_choice_keyboard() -> ReplyKeyboardMarkup:
    """
    Contacts choice keyboard for registration.

    Returns:
        ReplyKeyboardMarkup with contacts choice options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="✅ Да, оставить контакты"),
    )
    builder.row(
        KeyboardButton(text="⏭ Пропустить"),
    )

    return builder.as_markup(resize_keyboard=True)
