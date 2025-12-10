"""
Financial keyboards module.

This module contains keyboards related to financial operations:
- Financial password (finpass) operations
- Password recovery
- Show password after registration
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def finpass_input_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for financial password input with cancel button.

    Returns:
        ReplyKeyboardMarkup with cancel option
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="❌ Отменить вывод"),
    )

    return builder.as_markup(resize_keyboard=True)


def finpass_recovery_keyboard() -> ReplyKeyboardMarkup:
    """
    Financial password recovery keyboard.

    Returns:
        ReplyKeyboardMarkup with recovery options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="❌ Отмена"),
    )
    builder.row(
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def finpass_recovery_type_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for choosing recovery type.

    Returns:
        ReplyKeyboardMarkup with recovery type options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="🔑 Только пароль"),
    )
    builder.row(
        KeyboardButton(text="💼 Пароль + Новый кошелёк"),
    )
    builder.row(
        KeyboardButton(text="❌ Отмена"),
    )

    return builder.as_markup(resize_keyboard=True)


def finpass_recovery_confirm_keyboard() -> ReplyKeyboardMarkup:
    """
    Financial password recovery confirmation keyboard.

    Returns:
        ReplyKeyboardMarkup with confirm/cancel buttons
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="✅ Отправить заявку"),
    )
    builder.row(
        KeyboardButton(text="❌ Отменить"),
    )

    return builder.as_markup(resize_keyboard=True)


def show_password_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard to show password again after registration.

    Returns:
        ReplyKeyboardMarkup with show password button
    """
    builder = ReplyKeyboardBuilder()

    builder.row(KeyboardButton(text="🔑 Показать пароль ещё раз"))
    builder.row(KeyboardButton(text="📊 Главное меню"))

    return builder.as_markup(resize_keyboard=True)
