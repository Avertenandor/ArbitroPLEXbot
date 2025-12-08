"""
Main admin keyboards module.

Contains the primary admin panel keyboard and its helper function.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_admin_keyboard_from_data(data: dict) -> ReplyKeyboardMarkup:
    """
    Get admin keyboard using role flags from handler data.

    Args:
        data: Handler data dict. Expected keys:
            - is_super_admin: bool
            - is_extended_admin: bool

    Returns:
        ReplyKeyboardMarkup with admin options filtered by role.
    """
    is_super_admin = data.get("is_super_admin", False)
    is_extended_admin = data.get("is_extended_admin", False)
    return admin_keyboard(
        is_super_admin=is_super_admin,
        is_extended_admin=is_extended_admin,
    )


def admin_keyboard(
    is_super_admin: bool = False,
    is_extended_admin: bool = False,
) -> ReplyKeyboardMarkup:
    """
    Admin panel reply keyboard.

    Args:
        is_super_admin: Whether current admin is super admin
        is_extended_admin: Whether current admin is extended admin

    Returns:
        ReplyKeyboardMarkup with admin options, filtered by role.
    """
    builder = ReplyKeyboardBuilder()

    # Common buttons for ALL admins (Basic, Extended, Super)
    builder.row(KeyboardButton(text="📊 Статистика"))
    builder.row(KeyboardButton(text="👥 Управление пользователями"))
    builder.row(
        KeyboardButton(text="💸 Заявки на вывод"),
        KeyboardButton(text="📋 История выводов"),
    )
    builder.row(
        KeyboardButton(text="📢 Рассылка"),
        KeyboardButton(text="🆘 Техподдержка"),
    )

    # Financial Reports & Finpass Recovery (Safe for all admins per request)
    builder.row(
        KeyboardButton(text="💰 Финансовая отчётность"),
        KeyboardButton(text="🔑 Восстановление пароля"),
    )

    # User inquiries (questions from users)
    builder.row(KeyboardButton(text="📨 Обращения от пользователей"))

    # Referral stats
    builder.row(KeyboardButton(text="📊 Реферальная статистика"))

    builder.row(KeyboardButton(text="📝 Просмотр сообщений пользователей"))

    # AI Assistant - available for all admins
    builder.row(KeyboardButton(text="🤖 AI Помощник"))

    # Knowledge Base - available for all admins
    builder.row(KeyboardButton(text="📚 База знаний"))

    # Sensitive controls - Extended/Super only
    if is_extended_admin or is_super_admin:
        builder.row(
            KeyboardButton(text="🔐 Управление кошельком"),
            KeyboardButton(text="📡 Блокчейн Настройки"),
        )
        builder.row(
            KeyboardButton(text="🚫 Управление черным списком"),
        )
        builder.row(KeyboardButton(text="💰 Управление депозитами"))
        builder.row(KeyboardButton(text="🚨 Аварийные стопы"))

    # Super Admin only
    if is_super_admin:
        builder.row(KeyboardButton(text="👥 Управление админами"))
        builder.row(KeyboardButton(text="📋 Логи действий"))
        builder.row(KeyboardButton(text="⏰ Расписание задач"))
        builder.row(KeyboardButton(text="🔑 Управление мастер-ключом"))

    builder.row(KeyboardButton(text="◀️ Главное меню"))

    return builder.as_markup(resize_keyboard=True)
