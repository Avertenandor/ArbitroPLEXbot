"""
User management keyboards for admin panel.

Contains keyboards for user listing, searching, blocking, and profile management.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def admin_users_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin users management keyboard.

    Returns:
        ReplyKeyboardMarkup with user management options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="🔍 Найти пользователя"),
    )
    builder.row(
        KeyboardButton(text="👥 Список пользователей"),
    )
    builder.row(
        KeyboardButton(text="🚫 Заблокировать пользователя"),
    )
    builder.row(
        KeyboardButton(text="⚠️ Терминировать аккаунт"),
    )
    builder.row(
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def admin_user_list_keyboard(
    users: list,
    page: int = 1,
    total_pages: int = 1,
) -> ReplyKeyboardMarkup:
    """
    Keyboard with user buttons for admin selection.

    Args:
        users: List of User objects
        page: Current page
        total_pages: Total pages

    Returns:
        ReplyKeyboardMarkup with user buttons
    """
    builder = ReplyKeyboardBuilder()

    # User buttons (2 per row)
    for i in range(0, len(users), 2):
        row_buttons = []
        u1 = users[i]
        label1 = f"@{u1.username}" if u1.username else f"ID {u1.telegram_id}"
        # Button text format: "🆔 {id}: {label}" to easily parse ID later
        row_buttons.append(KeyboardButton(text=f"🆔 {u1.id}: {label1}"))

        if i + 1 < len(users):
            u2 = users[i + 1]
            label2 = f"@{u2.username}" if u2.username else f"ID {u2.telegram_id}"
            row_buttons.append(KeyboardButton(text=f"🆔 {u2.id}: {label2}"))

        builder.row(*row_buttons)

    # Navigation
    nav_buttons = []
    if total_pages > 1:
        if page > 1:
            nav_buttons.append(KeyboardButton(text="⬅ Предыдущая"))
        if page < total_pages:
            nav_buttons.append(KeyboardButton(text="Следующая ➡"))

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(
        KeyboardButton(text="👥 Управление пользователями"),
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def admin_user_profile_keyboard(user_is_blocked: bool) -> ReplyKeyboardMarkup:
    """
    Keyboard for managing a specific user.

    Args:
        user_is_blocked: Whether the user is currently blocked

    Returns:
        ReplyKeyboardMarkup with user profile actions
    """
    builder = ReplyKeyboardBuilder()

    block_text = "✅ Разблокировать" if user_is_blocked else "🚫 Заблокировать"

    builder.row(
        KeyboardButton(text="💳 Изменить баланс"),
        KeyboardButton(text=block_text),
    )
    builder.row(
        KeyboardButton(text="📜 История транзакций"),
        KeyboardButton(text="👥 Рефералы"),
    )
    builder.row(
        KeyboardButton(text="🔄 Сканировать депозит"),
        KeyboardButton(text="⚠️ Терминировать аккаунт"),
    )
    builder.row(
        KeyboardButton(text="◀️ К списку пользователей"),
        KeyboardButton(text="👑 Админ-панель"),
    )
    return builder.as_markup(resize_keyboard=True)
