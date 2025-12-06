"""
Menu keyboards module.

This module contains standard menu keyboards for various user actions:
- Balance menu
- Deposit menu
- Withdrawal menu
- Referral menu
- Settings menu
- Profile menu
- Contact management menus
- Wallet menu
- Support menu
- Notification settings
- Submenu keyboards
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# Import from submodules
from .contacts import (
    contact_input_keyboard,
    contact_update_menu_keyboard,
    contacts_choice_keyboard,
)
from .financial import (
    balance_menu_keyboard,
    deposit_menu_keyboard,
    earnings_dashboard_keyboard,
    wallet_menu_keyboard,
    withdrawal_menu_keyboard,
)
from .helpers import add_navigation_buttons, build_level_button_text
from .referral import referral_menu_keyboard
from .settings import (
    notification_settings_reply_keyboard,
    profile_menu_keyboard,
    settings_menu_keyboard,
)


def support_keyboard() -> ReplyKeyboardMarkup:
    """
    Support menu reply keyboard.

    Returns:
        ReplyKeyboardMarkup with support options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="✉️ Создать обращение"),
    )
    builder.row(
        KeyboardButton(text="📋 Мои обращения"),
    )
    builder.row(
        KeyboardButton(text="❓ FAQ"),
    )
    builder.row(
        KeyboardButton(text="⬅ Назад"),
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def instructions_keyboard(
    levels_status: dict[int, dict] | None = None,
) -> ReplyKeyboardMarkup:
    """
    Instructions keyboard with deposit levels and detail option.

    Args:
        levels_status: Optional dict with level statuses

    Returns:
        ReplyKeyboardMarkup with instructions options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="📖 Подробная инструкция"),
    )

    default_amounts = {1: 10, 2: 50, 3: 100, 4: 150, 5: 300}

    for level in [1, 2, 3, 4, 5]:
        button_text = build_level_button_text(level, levels_status, default_amounts)
        builder.row(KeyboardButton(text=button_text))

    builder.row(
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def finances_submenu_keyboard() -> ReplyKeyboardMarkup:
    """
    Finances submenu keyboard.

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


# Public exports for backward compatibility
__all__ = [
    # Financial menus
    "balance_menu_keyboard",
    "deposit_menu_keyboard",
    "withdrawal_menu_keyboard",
    "wallet_menu_keyboard",
    "earnings_dashboard_keyboard",
    # Referral menu
    "referral_menu_keyboard",
    # Settings menus
    "settings_menu_keyboard",
    "profile_menu_keyboard",
    "notification_settings_reply_keyboard",
    # Contact menus
    "contact_update_menu_keyboard",
    "contact_input_keyboard",
    "contacts_choice_keyboard",
    # Support and instructions
    "support_keyboard",
    "instructions_keyboard",
    # Submenu keyboards
    "finances_submenu_keyboard",
    "cabinet_submenu_keyboard",
    "help_submenu_keyboard",
    # Helpers
    "build_level_button_text",
    "add_navigation_buttons",
]
