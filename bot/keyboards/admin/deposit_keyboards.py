"""
Deposit management keyboards for admin panel.

Contains keyboards for managing deposit levels, ROI corridors, and deposit settings.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def admin_deposit_settings_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin deposit settings keyboard.

    Returns:
        ReplyKeyboardMarkup with deposit settings options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="⚙️ Настроить уровни депозитов"),
    )
    builder.row(
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def admin_deposit_management_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin deposit management main menu keyboard.

    Returns:
        ReplyKeyboardMarkup with deposit management options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="📊 Статистика по депозитам"),
    )
    builder.row(
        KeyboardButton(text="🔍 Найти депозиты пользователя"),
    )
    builder.row(
        KeyboardButton(text="⚙️ Управление уровнями"),
    )
    builder.row(
        KeyboardButton(text="📋 Pending депозиты"),
    )
    builder.row(
        KeyboardButton(text="💰 Коридоры доходности"),
    )
    builder.row(
        KeyboardButton(text="📈 ROI статистика"),
    )
    builder.row(
        KeyboardButton(text="◀️ Назад в админ-панель"),
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def admin_deposit_levels_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin deposit levels selection keyboard.

    Returns:
        ReplyKeyboardMarkup with level selection buttons
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="Уровень 1"),
        KeyboardButton(text="Уровень 2"),
    )
    builder.row(
        KeyboardButton(text="Уровень 3"),
        KeyboardButton(text="Уровень 4"),
    )
    builder.row(
        KeyboardButton(text="Уровень 5"),
    )
    builder.row(
        KeyboardButton(text="🔢 Изм. макс. уровень"),
    )
    builder.row(
        KeyboardButton(text="◀️ Назад в админ-панель"),
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def admin_deposit_level_actions_keyboard(
    level: int, is_active: bool
) -> ReplyKeyboardMarkup:
    """
    Admin deposit level actions keyboard.

    Args:
        level: Deposit level number (1-5)
        is_active: Whether level is currently active

    Returns:
        ReplyKeyboardMarkup with level action buttons
    """
    builder = ReplyKeyboardBuilder()

    # ROI Corridor management button (main feature)
    builder.row(
        KeyboardButton(text="💰 Настроить коридор доходности"),
    )

    # Enable/Disable level button
    if is_active:
        builder.row(
            KeyboardButton(text="❌ Отключить уровень"),
        )
    else:
        builder.row(
            KeyboardButton(text="✅ Включить уровень"),
        )

    # Back button
    builder.row(
        KeyboardButton(text="◀️ Назад к уровням"),
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def admin_roi_corridor_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    ROI corridor management menu keyboard.

    Returns:
        ReplyKeyboardMarkup with ROI corridor menu options
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="⚙️ Настроить коридоры"))
    builder.row(KeyboardButton(text="💵 Настроить суммы уровней"))
    builder.row(KeyboardButton(text="📊 Текущие настройки"))
    builder.row(KeyboardButton(text="📜 История изменений"))
    builder.row(KeyboardButton(text="⏱ Настроить период начисления"))
    builder.row(
        KeyboardButton(text="◀️ Назад в управление депозитами")
    )
    builder.row(KeyboardButton(text="👑 Админ-панель"))
    return builder.as_markup(resize_keyboard=True)


def admin_roi_level_select_keyboard() -> ReplyKeyboardMarkup:
    """
    Level selection keyboard for ROI corridor management.

    Returns:
        ReplyKeyboardMarkup with level selection buttons
    """
    builder = ReplyKeyboardBuilder()
    for i in range(1, 6):
        builder.row(KeyboardButton(text=f"Уровень {i}"))
    builder.row(
        KeyboardButton(text="◀️ Отмена"),
        KeyboardButton(text="👑 Админ-панель"),
    )
    return builder.as_markup(resize_keyboard=True)


def admin_roi_mode_select_keyboard() -> ReplyKeyboardMarkup:
    """
    Mode selection keyboard for ROI corridor.

    Returns:
        ReplyKeyboardMarkup with mode selection buttons
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🎲 Custom (случайный из коридора)"))
    builder.row(
        KeyboardButton(text="📊 Поровну (фиксированный для всех)")
    )
    builder.row(
        KeyboardButton(text="◀️ Отмена"),
        KeyboardButton(text="👑 Админ-панель"),
    )
    return builder.as_markup(resize_keyboard=True)


def admin_roi_applies_to_keyboard() -> ReplyKeyboardMarkup:
    """
    Application scope selection keyboard.

    Returns:
        ReplyKeyboardMarkup with application scope buttons
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="⚡️ Применить к текущей сессии"))
    builder.row(KeyboardButton(text="⏭ Применить к следующей сессии"))
    builder.row(
        KeyboardButton(text="◀️ Отмена"),
        KeyboardButton(text="👑 Админ-панель"),
    )
    return builder.as_markup(resize_keyboard=True)


def admin_roi_confirmation_keyboard() -> ReplyKeyboardMarkup:
    """
    Confirmation keyboard for ROI corridor settings.

    Returns:
        ReplyKeyboardMarkup with confirmation buttons
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="✅ Да, применить"))
    builder.row(KeyboardButton(text="❌ Нет, отменить"))
    return builder.as_markup(resize_keyboard=True)
