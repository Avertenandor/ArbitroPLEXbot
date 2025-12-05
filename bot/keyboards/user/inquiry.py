"""
Inquiry keyboards module.

This module contains keyboards for user inquiry (question) functionality:
- Inquiry input
- Active inquiry dialog
- Waiting for admin response
- Inquiry history
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def inquiry_input_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for inquiry input screen.

    Returns:
        ReplyKeyboardMarkup with cancel option
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Отмена"))
    builder.row(KeyboardButton(text="◀️ Главное меню"))
    return builder.as_markup(resize_keyboard=True)


def inquiry_dialog_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for active inquiry dialog (user side).

    Returns:
        ReplyKeyboardMarkup with dialog options
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="✅ Закрыть обращение"))
    builder.row(KeyboardButton(text="◀️ Главное меню"))
    return builder.as_markup(resize_keyboard=True)


def inquiry_waiting_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard while waiting for admin response.

    Returns:
        ReplyKeyboardMarkup with waiting options
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📝 Дополнить вопрос"))
    builder.row(KeyboardButton(text="📜 Мои обращения"))
    builder.row(KeyboardButton(text="❌ Отменить обращение"))
    builder.row(KeyboardButton(text="◀️ Главное меню"))
    return builder.as_markup(resize_keyboard=True)


def inquiry_history_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for inquiry history view.

    Returns:
        ReplyKeyboardMarkup with history options
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❓ Задать новый вопрос"))
    builder.row(KeyboardButton(text="◀️ Главное меню"))
    return builder.as_markup(resize_keyboard=True)
