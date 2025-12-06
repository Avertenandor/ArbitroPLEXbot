"""
Settings menu keyboards module.

This module contains keyboards related to user settings:
- Settings menu
- Profile menu
- Notification settings
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def settings_menu_keyboard(language: str | None = None) -> ReplyKeyboardMarkup:
    """
    Settings menu reply keyboard.

    Args:
        language: User's preferred language (currently unused, for future i18n)

    Returns:
        ReplyKeyboardMarkup with settings options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="👤 Мой профиль"),
    )
    builder.row(
        KeyboardButton(text="💳 Мой кошелек"),
    )
    builder.row(
        KeyboardButton(text="🔔 Настройки уведомлений"),
    )
    builder.row(
        KeyboardButton(text="📝 Обновить контакты"),
    )
    builder.row(
        KeyboardButton(text="🌐 Изменить язык"),
    )
    builder.row(
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def profile_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Profile menu keyboard.

    Returns:
        ReplyKeyboardMarkup with profile options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="📂 Скачать отчет"),
    )
    builder.row(
        KeyboardButton(text="◀️ Назад"),
    )

    return builder.as_markup(resize_keyboard=True)


def notification_settings_reply_keyboard(
    deposit_enabled: bool,
    withdrawal_enabled: bool,
    roi_enabled: bool = True,
    marketing_enabled: bool = False,
) -> ReplyKeyboardMarkup:
    """
    Notification settings reply keyboard.

    Args:
        deposit_enabled: Whether deposit notifications are enabled
        withdrawal_enabled: Whether withdrawal notifications are enabled
        roi_enabled: Whether ROI notifications are enabled
        marketing_enabled: Whether marketing notifications are enabled

    Returns:
        ReplyKeyboardMarkup with notification toggle buttons
    """
    builder = ReplyKeyboardBuilder()

    # Deposit notifications toggle
    deposit_text = (
        "✅ Уведомления о депозитах" if deposit_enabled
        else "❌ Уведомления о депозитах"
    )
    builder.row(
        KeyboardButton(text=deposit_text),
    )

    # Withdrawal notifications toggle
    withdrawal_text = (
        "✅ Уведомления о выводах" if withdrawal_enabled
        else "❌ Уведомления о выводах"
    )
    builder.row(
        KeyboardButton(text=withdrawal_text),
    )

    # ROI notifications toggle
    roi_text = (
        "✅ Уведомления о ROI" if roi_enabled
        else "❌ Уведомления о ROI"
    )
    builder.row(
        KeyboardButton(text=roi_text),
    )

    # Marketing notifications toggle
    marketing_text = (
        "✅ Маркетинговые уведомления" if marketing_enabled
        else "❌ Маркетинговые уведомления"
    )
    builder.row(
        KeyboardButton(text=marketing_text),
    )

    builder.row(
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)
