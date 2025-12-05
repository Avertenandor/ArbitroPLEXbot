"""
Main menu keyboard module.

This module contains the main menu reply keyboard builder.
The main menu is the central navigation point for users.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from loguru import logger

from app.models.blacklist import Blacklist, BlacklistActionType
from app.models.user import User


def main_menu_reply_keyboard(
    user: User | None = None,
    blacklist_entry: Blacklist | None = None,
    is_admin: bool = False,
) -> ReplyKeyboardMarkup:
    """
    Main menu reply keyboard.

    Conditionally shows buttons based on user status (e.g., blocked, admin, unregistered).

    Args:
        user: The current user object (optional). If None, shows reduced menu for unregistered users.
        blacklist_entry: The user's blacklist entry, if any (optional).
        is_admin: Whether the user is an admin (optional).

    Returns:
        ReplyKeyboardMarkup with main menu buttons
    """
    # Safely access telegram_id
    user_id = user.id if user else None

    # Fix for AttributeError: 'User' object has no attribute 'telegram_id'
    # In fallback handler, message.from_user is a Telegram User object (aiogram),
    # which has 'id', NOT 'telegram_id'.
    # Our database User model (app.models.user) has 'telegram_id'.
    # We need to handle both cases.
    telegram_id = None
    if user:
        if hasattr(user, 'telegram_id'):
            telegram_id = user.telegram_id
        elif hasattr(user, 'id'):
            telegram_id = user.id

    logger.debug(
        f"[KEYBOARD] main_menu_reply_keyboard called: "
        f"user_id={user_id}, telegram_id={telegram_id}, "
        f"is_admin={is_admin}, "
        f"blacklist_active={blacklist_entry.is_active if blacklist_entry else False}"
    )

    builder = ReplyKeyboardBuilder()

    # If user is blocked (with appeal option), show only appeal button
    if (
        user
        and blacklist_entry
        and blacklist_entry.is_active
        and blacklist_entry.action_type == BlacklistActionType.BLOCKED
    ):
        # Keep this on INFO as it's a rare security event
        logger.info(f"[KEYBOARD] User {telegram_id} is blocked, showing appeal button only")
        builder.row(
            KeyboardButton(text="📝 Подать апелляцию"),
        )
    elif user is None:
        # Reduced menu for unregistered users
        logger.debug(f"[KEYBOARD] Building reduced menu for unregistered user {telegram_id}")
        builder.row(
            KeyboardButton(text="📖 Инструкции"),
        )
        builder.row(
            KeyboardButton(text="💬 Поддержка"),
        )
        builder.row(
            KeyboardButton(text="📝 Регистрация"),
        )
    else:
        # Standard menu for registered users
        logger.debug(f"[KEYBOARD] Building standard menu for user {telegram_id}")
        builder.row(
            KeyboardButton(text="💰 Депозит"),
            KeyboardButton(text="💸 Вывод"),
        )
        builder.row(
            KeyboardButton(text="📦 Мои депозиты"),
            KeyboardButton(text="🔄 Обновить депозит"),
        )
        builder.row(
            KeyboardButton(text="👥 Рефералы"),
            KeyboardButton(text="📊 Баланс"),
        )
        builder.row(
            KeyboardButton(text="💰 Баланс кошелька"),
        )
        builder.row(
            KeyboardButton(text="💬 Поддержка"),
            KeyboardButton(text="❓ Задать вопрос"),
        )
        builder.row(
            KeyboardButton(text="📖 Инструкции"),
            KeyboardButton(text="📜 История операций"),
        )
        builder.row(
            KeyboardButton(text="📊 Калькулятор"),
            KeyboardButton(text="⚙️ Настройки"),
        )
        builder.row(
            KeyboardButton(text="🔐 Получить финпароль"),
            KeyboardButton(text="🔑 Восстановить финпароль"),
        )
        builder.row(
            KeyboardButton(text="🐰 Купить кролика"),
            KeyboardButton(text="📋 Правила"),
        )
        builder.row(
            KeyboardButton(text="🌐 Инструменты нашей экосистемы"),
        )

        # Add admin panel button for admins
        if is_admin:
            logger.info(f"[KEYBOARD] Adding admin panel button for user {telegram_id}")
            builder.row(
                KeyboardButton(text="👑 Админ-панель"),
            )

            # Add master key button for super admin
            from app.config.settings import settings
            super_admin_id = settings.super_admin_telegram_id
            is_super = telegram_id and telegram_id == super_admin_id

            logger.debug(
                f"[KEYBOARD] Super admin check: telegram_id={telegram_id}, "
                f"super_admin_id={super_admin_id}, is_super={is_super}"
            )
            
            if is_super:
                logger.info(
                    f"[KEYBOARD] Adding master key button for super admin {telegram_id}"
                )
                builder.row(
                    KeyboardButton(text="🔑 Мой мастер-ключ"),
                )

        # Log for non-admin case is handled by the if block above

    keyboard = builder.as_markup(resize_keyboard=True)
    logger.info(f"[KEYBOARD] Keyboard created for user {telegram_id}, buttons count: {len(keyboard.keyboard)}")
    return keyboard
