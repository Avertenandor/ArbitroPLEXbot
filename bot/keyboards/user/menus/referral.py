"""
Referral menu keyboards module.

This module contains keyboards related to referral system:
- Referral menu with all referral features
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def referral_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Referral menu reply keyboard.

    Returns:
        ReplyKeyboardMarkup with referral options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="🌳 Моя структура"),
        KeyboardButton(text="💰 Мой заработок"),
    )
    builder.row(
        KeyboardButton(text="📊 Статистика рефералов"),
        KeyboardButton(text="📈 Аналитика"),
    )
    builder.row(
        KeyboardButton(text="🏆 ТОП партнёров"),
        KeyboardButton(text="📢 Промо-материалы"),
    )
    builder.row(
        KeyboardButton(text="💬 Написать спонсору"),
        KeyboardButton(text="📬 Входящие от рефералов"),
    )
    builder.row(
        KeyboardButton(text="👤 Кто меня пригласил"),
        KeyboardButton(text="📋 Скопировать ссылку"),
    )
    builder.row(
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)
