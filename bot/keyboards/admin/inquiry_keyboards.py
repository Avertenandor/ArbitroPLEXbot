"""
User inquiry keyboards for admin panel.

Contains keyboards for managing user inquiries (questions to sponsor/admin).
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def admin_inquiry_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin inquiry management menu.

    Returns:
        ReplyKeyboardMarkup with inquiry options
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📬 Новые обращения"))
    builder.row(KeyboardButton(text="📋 Мои обращения"))
    builder.row(KeyboardButton(text="✅ Закрытые обращения"))
    builder.row(KeyboardButton(text="👑 Админ-панель"))
    return builder.as_markup(resize_keyboard=True)


def admin_inquiry_list_keyboard(
    inquiries: list,
    page: int = 1,
    total_pages: int = 1,
) -> ReplyKeyboardMarkup:
    """
    Keyboard with inquiry buttons for admin selection.

    Args:
        inquiries: List of UserInquiry objects
        page: Current page
        total_pages: Total pages

    Returns:
        ReplyKeyboardMarkup with inquiry selection
    """
    builder = ReplyKeyboardBuilder()

    for inquiry in inquiries:
        # Show user info and question preview
        username = inquiry.user.username or f"ID:{inquiry.user_id}"
        preview = inquiry.initial_question[:30] + "..."
        builder.row(
            KeyboardButton(text=f"📩 #{inquiry.id} {username}: {preview}")
        )

    # Pagination
    nav_buttons = []
    if page > 1:
        nav_buttons.append(KeyboardButton(text="⬅️ Пред. стр."))
    if page < total_pages:
        nav_buttons.append(KeyboardButton(text="➡️ След. стр."))
    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(KeyboardButton(text="🔄 Обновить список"))
    builder.row(KeyboardButton(text="◀️ Назад к обращениям"))
    return builder.as_markup(resize_keyboard=True)


def admin_inquiry_detail_keyboard(
    is_assigned: bool = False,
) -> ReplyKeyboardMarkup:
    """
    Keyboard for viewing specific inquiry.

    Args:
        is_assigned: Whether inquiry is assigned to current admin

    Returns:
        ReplyKeyboardMarkup with inquiry actions
    """
    builder = ReplyKeyboardBuilder()

    if not is_assigned:
        builder.row(KeyboardButton(text="✋ Взять в работу"))
    else:
        builder.row(KeyboardButton(text="💬 Ответить пользователю"))
        builder.row(KeyboardButton(text="✅ Закрыть обращение"))

    builder.row(KeyboardButton(text="◀️ Назад к списку"))
    builder.row(KeyboardButton(text="👑 Админ-панель"))
    return builder.as_markup(resize_keyboard=True)


def admin_inquiry_response_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard while admin is writing response.

    Returns:
        ReplyKeyboardMarkup with cancel option
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Отмена"))
    builder.row(KeyboardButton(text="◀️ Назад к обращению"))
    return builder.as_markup(resize_keyboard=True)
