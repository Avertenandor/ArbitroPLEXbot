"""
Deposit menu keyboards module.

This module contains all deposit-related keyboards:
- Deposit menu with levels
- Instructions keyboard
- Deposit levels keyboard with corridors
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def deposit_menu_keyboard(
    levels_status: dict[int, dict] | None = None,
) -> ReplyKeyboardMarkup:
    """
    Deposit menu reply keyboard with status indicators and corridors.

    Args:
        levels_status: Optional dict with level statuses from
            DepositValidationService.get_available_levels()

    Returns:
        ReplyKeyboardMarkup with deposit options
    """
    builder = ReplyKeyboardBuilder()

    # Default corridors if statuses not provided (including test level 0)
    default_corridors = {
        0: (30, 100),      # Test: $30-$100
        1: (100, 500),     # Level 1: $100-$500
        2: (700, 1200),    # Level 2: $700-$1200
        3: (1400, 2200),   # Level 3: $1400-$2200
        4: (2500, 3500),   # Level 4: $2500-$3500
        5: (4000, 7000),   # Level 5: $4000-$7000
    }

    # Level emoji mapping (including test level)
    level_emojis = {0: "🎯", 1: "💰", 2: "💎", 3: "🏆", 4: "👑", 5: "🚀"}

    # Level display names
    level_names = {
        0: "Тестовый",
        1: "Уровень 1",
        2: "Уровень 2",
        3: "Уровень 3",
        4: "Уровень 4",
        5: "Уровень 5"
    }

    # All levels including test (0)
    for level in [0, 1, 2, 3, 4, 5]:
        emoji = level_emojis[level]
        display_name = level_names[level]

        if levels_status and level in levels_status:
            level_info = levels_status[level]
            min_amt = level_info.get("min_amount") or default_corridors[level][0]
            max_amt = level_info.get("max_amount") or default_corridors[level][1]
            status = level_info["status"]
            corridor_str = f"${int(min_amt)}-${int(max_amt)}"

            # Build button text with status indicator
            if status == "active":
                button_text = f"✅ {emoji} {display_name} ({corridor_str}) - Активен"
            elif status == "available":
                button_text = f"{emoji} {display_name} ({corridor_str})"
            else:
                # unavailable - show reason in button
                error = level_info.get("error", "")
                if (
                    "уже приобретен" in error.lower()
                    or "уже куплен" in error.lower()
                ):
                    button_text = f"✅ {emoji} {display_name} ({corridor_str}) - Куплен"
                elif (
                    "необходимо сначала" in error.lower()
                    or "предыдущ" in error.lower()
                ):
                    button_text = f"🔒 {emoji} {display_name} ({corridor_str})"
                elif "временно недоступен" in error.lower():
                    button_text = f"🔒 {emoji} {display_name} ({corridor_str}) - Закрыт"
                else:
                    button_text = f"🔒 {emoji} {display_name} ({corridor_str})"
        else:
            # Fallback to default corridors
            min_amt, max_amt = default_corridors[level]
            corridor_str = f"${min_amt}-${max_amt}"
            button_text = f"{emoji} {display_name} ({corridor_str})"

        builder.row(KeyboardButton(text=button_text))

    builder.row(
        KeyboardButton(text="◀️ Назад"),
    )
    builder.row(
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def instructions_keyboard(
    levels_status: dict[int, dict] | None = None,
) -> ReplyKeyboardMarkup:
    """
    Instructions keyboard with deposit levels and detail option.

    Args:
        levels_status: Optional dict with level statuses from
            DepositValidationService.get_available_levels()

    Returns:
        ReplyKeyboardMarkup with instructions options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="📖 Подробная инструкция"),
    )

    # Default amounts if statuses not provided
    default_amounts = {1: 10, 2: 50, 3: 100, 4: 150, 5: 300}

    # Level emoji mapping
    level_emojis = {1: "💰", 2: "💎", 3: "🏆", 4: "👑", 5: "🚀"}

    for level in [1, 2, 3, 4, 5]:
        emoji = level_emojis[level]

        if levels_status and level in levels_status:
            level_info = levels_status[level]
            amount = level_info["amount"]
            status = level_info["status"]

            # Build button text with status indicator
            if status == "active":
                button_text = f"✅ {emoji} Уровень {level} ({amount} USDT) - Активен"
            elif status == "available":
                button_text = f"{emoji} Уровень {level} ({amount} USDT)"
            else:
                # unavailable - show reason in button
                error = level_info.get("error", "")
                if "необходимо сначала купить" in error:
                    button_text = (
                        f"🔒 {emoji} Уровень {level} "
                        f"({amount} USDT) - Нет предыдущего"
                    )
                elif "временно недоступен" in error:
                    button_text = (
                        f"🔒 {emoji} Уровень {level} "
                        f"({amount} USDT) - Закрыт"
                    )
                else:
                    button_text = (
                        f"🔒 {emoji} Уровень {level} "
                        f"({amount} USDT) - Недоступен"
                    )
        else:
            # Fallback to default
            amount = default_amounts[level]
            button_text = f"{emoji} Уровень {level} ({amount} USDT)"

        builder.row(KeyboardButton(text=button_text))

    builder.row(
        KeyboardButton(text="◀️ Назад"),
    )
    builder.row(
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def deposit_levels_keyboard(
    levels_status: dict | None = None
) -> ReplyKeyboardMarkup:
    """
    Клавиатура выбора уровня депозита
    с коридорами сумм.

    Args:
        levels_status: Словарь со статусами уровней депозита.
            Пример: {
                "test": {"status": "available", "min": 30, "max": 100},
                "level_1": {
                    "status": "locked",
                    "min": 100,
                    "max": 500,
                    "reason": "Нужен тестовый"
                },
                "level_2": {"status": "active", "min": 500, "max": 1000},
                ...
            }

    Returns:
        ReplyKeyboardMarkup: Клавиатура с уровнями депозита
    """
    builder = ReplyKeyboardBuilder()

    levels = [
        ("test", "🎯 Тестовый"),
        ("level_1", "💰 Уровень 1"),
        ("level_2", "💎 Уровень 2"),
        ("level_3", "🏆 Уровень 3"),
        ("level_4", "👑 Уровень 4"),
        ("level_5", "🚀 Уровень 5"),
    ]

    for level_type, emoji_name in levels:
        if levels_status and level_type in levels_status:
            info = levels_status[level_type]
            status = info.get("status", "locked")
            min_amt = info.get("min", 0)
            max_amt = info.get("max", 0)

            if status == "active":
                text = f"✅ {emoji_name} (${min_amt}-${max_amt}) - Активен"
            elif status == "available":
                text = f"{emoji_name} (${min_amt}-${max_amt})"
            else:  # locked
                text = f"🔒 {emoji_name} (${min_amt}-${max_amt})"
        else:
            text = f"🔒 {emoji_name}"

        builder.row(KeyboardButton(text=text))

    builder.row(KeyboardButton(text="◀️ Назад"))
    builder.row(KeyboardButton(text="📊 Главное меню"))
    return builder.as_markup(resize_keyboard=True)
