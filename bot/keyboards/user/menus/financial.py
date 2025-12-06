"""
Financial menu keyboards module.

This module contains keyboards related to financial operations:
- Balance menu
- Deposit menu
- Withdrawal menu
- Wallet menu
- Earnings dashboard
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from .helpers import build_level_button_text


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


def deposit_menu_keyboard(
    levels_status: dict[int, dict] | None = None,
) -> ReplyKeyboardMarkup:
    """
    Deposit menu reply keyboard with status indicators.

    Args:
        levels_status: Optional dict with level statuses from DepositValidationService.get_available_levels()

    Returns:
        ReplyKeyboardMarkup with deposit options
    """
    builder = ReplyKeyboardBuilder()

    # Default amounts if statuses not provided
    default_amounts = {1: 10, 2: 50, 3: 100, 4: 150, 5: 300}

    for level in [1, 2, 3, 4, 5]:
        if levels_status and level in levels_status:
            # Consume unused variable to avoid linter warnings
            levels_status[level].get("status_text", "")

        button_text = build_level_button_text(level, levels_status, default_amounts)
        builder.row(KeyboardButton(text=button_text))

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


def wallet_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Wallet menu keyboard.

    Returns:
        ReplyKeyboardMarkup with wallet options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(KeyboardButton(text="🔄 Сменить кошелек"))
    builder.row(
        KeyboardButton(text="⚙️ Настройки"),
        KeyboardButton(text="📊 Главное меню")
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
