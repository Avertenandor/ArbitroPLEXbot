"""
Main menu keyboard module.

This module contains the main menu keyboard and related submenu keyboards.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Main menu keyboard.

    Returns:
        ReplyKeyboardMarkup with main menu options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="💰 Финансы"),
        KeyboardButton(text="🏦 Кабинет"),
    )

    builder.row(
        KeyboardButton(text="👥 Партнёры"),
        KeyboardButton(text="⚙️ Настройки"),
    )

    builder.row(
        KeyboardButton(text="❓ Помощь"),
    )

    return builder.as_markup(resize_keyboard=True)


def finances_submenu_keyboard() -> ReplyKeyboardMarkup:
    """
    Finances submenu keyboard.

    Contains all financial operations:
    - Deposit
    - Withdrawal
    - Balance overview
    - Earnings dashboard

    Returns:
        ReplyKeyboardMarkup with finances options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="💰 Депозит"),
        KeyboardButton(text="💸 Вывод"),
    )

    builder.row(
        KeyboardButton(text="📈 Мой заработок"),
        KeyboardButton(text="📊 Мои средства"),
    )

    builder.row(
        KeyboardButton(text="◀️ Назад"),
    )

    return builder.as_markup(resize_keyboard=True)


def cabinet_submenu_keyboard() -> ReplyKeyboardMarkup:
    """
    User cabinet submenu keyboard.

    Contains user's portfolio and reports:
    - Active deposits
    - Transaction history
    - Calculator
    - Earnings dashboard

    Returns:
        ReplyKeyboardMarkup with cabinet options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="📦 Мои депозиты"),
        KeyboardButton(text="📜 История операций"),
    )

    builder.row(
        KeyboardButton(text="📊 Калькулятор"),
        KeyboardButton(text="💰 Мой заработок"),
    )

    builder.row(
        KeyboardButton(text="◀️ Назад"),
    )

    return builder.as_markup(resize_keyboard=True)


def help_submenu_keyboard() -> ReplyKeyboardMarkup:
    """
    Help submenu keyboard.

    Contains all help and support options:
    - FAQ
    - Instructions
    - Rules
    - Support contact
    - Back to main menu

    Returns:
        ReplyKeyboardMarkup with help options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="❓ FAQ"),
        KeyboardButton(text="📖 Инструкции"),
    )

    builder.row(
        KeyboardButton(text="📋 Правила"),
        KeyboardButton(text="✉️ Написать в поддержку"),
    )

    builder.row(
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)
