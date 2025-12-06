"""
Helper functions for menu keyboards.

This module contains utility functions and small helper keyboards
used across different menu keyboards.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def build_level_button_text(
    level: int,
    levels_status: dict[int, dict] | None = None,
    default_amounts: dict[int, int] | None = None,
) -> str:
    """
    Build button text for a deposit level based on its status.

    Args:
        level: Level number (1-5)
        levels_status: Optional dict with level statuses from DepositValidationService
        default_amounts: Default amounts for each level

    Returns:
        Formatted button text with appropriate status indicator
    """
    if default_amounts is None:
        default_amounts = {1: 10, 2: 50, 3: 100, 4: 150, 5: 300}

    if levels_status and level in levels_status:
        level_info = levels_status[level]
        amount = level_info["amount"]
        status = level_info["status"]

        # Build button text with status indicator
        if status == "active":
            return f"✅ Level {level} ({amount} USDT) - Активен"
        elif status == "available":
            return f"💰 Пополнить Level {level} ({amount} USDT)"
        else:
            # unavailable - show reason in button
            error = level_info.get("error", "")
            if "необходимо сначала купить" in error:
                return f"🔒 Level {level} ({amount} USDT) - Нет предыдущего"
            elif "временно недоступен" in error:
                return f"🔒 Level {level} ({amount} USDT) - Закрыт"
            else:
                return f"🔒 Level {level} ({amount} USDT) - Недоступен"
    else:
        # Fallback to default
        amount = default_amounts[level]
        return f"💰 Пополнить Level {level} ({amount} USDT)"


def add_navigation_buttons(
    builder,
    include_back: bool = False,
    include_main_menu: bool = True,
) -> None:
    """
    Add standard navigation buttons to a keyboard builder.

    Args:
        builder: ReplyKeyboardBuilder instance
        include_back: Whether to include back button
        include_main_menu: Whether to include main menu button
    """
    if include_back and include_main_menu:
        builder.row(
            KeyboardButton(text="◀️ Назад"),
            KeyboardButton(text="📊 Главное меню"),
        )
    elif include_back:
        builder.row(KeyboardButton(text="◀️ Назад"))
    elif include_main_menu:
        builder.row(KeyboardButton(text="📊 Главное меню"))


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
