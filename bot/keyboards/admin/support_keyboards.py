"""
Support ticket keyboards for admin panel.

Contains keyboards for managing user support tickets and requests.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def admin_support_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin support keyboard.

    Returns:
        ReplyKeyboardMarkup with support options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="📋 Список обращений"),
        KeyboardButton(text="🔍 Найти обращение"),
    )
    builder.row(
        KeyboardButton(text="📊 Статистика"),
        KeyboardButton(text="🙋‍♂️ Мои задачи"),
    )
    builder.row(
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def admin_support_ticket_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for viewing a specific ticket.

    Returns:
        ReplyKeyboardMarkup with ticket actions
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📝 Ответить"))
    builder.row(
        KeyboardButton(text="🔒 Закрыть"),
        KeyboardButton(text="↩️ Переоткрыть")
    )
    builder.row(KeyboardButton(text="✋ Взять в работу"))
    builder.row(
        KeyboardButton(text="◀️ Назад к списку"),
        KeyboardButton(text="👑 Админ-панель")
    )
    return builder.as_markup(resize_keyboard=True)


def admin_ticket_list_keyboard(
    tickets: list,
    page: int = 1,
    total_pages: int = 1,
) -> ReplyKeyboardMarkup:
    """
    Keyboard with ticket buttons for admin selection.

    Args:
        tickets: List of SupportTicket objects
        page: Current page
        total_pages: Total pages

    Returns:
        ReplyKeyboardMarkup with ticket buttons
    """
    builder = ReplyKeyboardBuilder()

    # Ticket buttons (2 per row)
    for i in range(0, len(tickets), 2):
        row_buttons = []
        # Button 1
        t1 = tickets[i]
        user_label1 = f"ID: {t1.user_id}"
        if t1.user and t1.user.username:
            user_label1 = f"@{t1.user.username}"
        row_buttons.append(KeyboardButton(text=f"🎫 #{t1.id} {user_label1}"))

        # Button 2 (if exists)
        if i + 1 < len(tickets):
            t2 = tickets[i + 1]
            user_label2 = f"ID: {t2.user_id}"
            if t2.user and t2.user.username:
                user_label2 = f"@{t2.user.username}"
            row_buttons.append(KeyboardButton(text=f"🎫 #{t2.id} {user_label2}"))

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
        KeyboardButton(text="🆘 Техподдержка"),
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)
