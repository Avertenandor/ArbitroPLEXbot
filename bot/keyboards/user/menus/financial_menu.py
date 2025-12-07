"""
Financial menu keyboards module.

This module contains all financial operation keyboards:
- Balance menu
- Withdrawal menu
- Earnings dashboard
- Finances submenu
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def balance_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Balance menu keyboard.

    Returns:
        ReplyKeyboardMarkup with balance options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="💰 Баланс"),
    )
    builder.row(
        KeyboardButton(text="📜 История операций"),
    )
    builder.row(
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def withdrawal_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Withdrawal menu reply keyboard.

    Returns:
        ReplyKeyboardMarkup with withdrawal options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="💸 Вывести всю сумму"),
    )
    builder.row(
        KeyboardButton(text="💵 Вывести указанную сумму"),
    )
    builder.row(
        KeyboardButton(text="📜 История выводов"),
    )
    builder.row(
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def earnings_dashboard_keyboard() -> ReplyKeyboardMarkup:
    """
    Earnings dashboard keyboard.

    Returns:
        ReplyKeyboardMarkup with earnings dashboard options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="💸 Вывести средства"),
    )
    builder.row(
        KeyboardButton(text="📜 История операций"),
    )
    builder.row(
        KeyboardButton(text="📊 Главное меню"),
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
    - My Wallet

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
        KeyboardButton(text="👛 Мой кошелек"),
    )

    builder.row(
        KeyboardButton(text="◀️ Назад"),
    )

    return builder.as_markup(resize_keyboard=True)
