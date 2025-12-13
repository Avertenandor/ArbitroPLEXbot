"""
Withdrawal management keyboards for admin panel.

Contains keyboards for viewing, approving, and managing withdrawal requests.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def admin_withdrawals_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin withdrawals management keyboard.

    Returns:
        ReplyKeyboardMarkup with withdrawal management options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="⏳ Ожидающие выводы"),
    )
    builder.row(
        KeyboardButton(text="📋 Одобренные выводы"),
        KeyboardButton(text="🚫 Отклоненные выводы"),
    )
    builder.row(
        KeyboardButton(text="⚙️ Настройки выплат"),
    )
    builder.row(
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def withdrawal_list_keyboard(
    withdrawals: list,
    page: int = 1,
    total_pages: int = 1,
) -> ReplyKeyboardMarkup:
    """
    Keyboard with withdrawal buttons for admin selection.

    Args:
        withdrawals: List of Transaction objects (pending withdrawals)
        page: Current page
        total_pages: Total pages

    Returns:
        ReplyKeyboardMarkup with withdrawal buttons
    """
    from bot.utils.formatters import format_usdt

    builder = ReplyKeyboardBuilder()

    # Withdrawal buttons (1 per row for clarity)
    for wd in withdrawals:
        amount_str = format_usdt(wd.amount)
        user_label = f"ID:{wd.user_id}"
        if hasattr(wd, "user") and wd.user and wd.user.username:
            user_label = f"@{wd.user.username}"
        # Neutral emoji for selection
        builder.row(
            KeyboardButton(text=f"💸 #{wd.id} | {amount_str} | {user_label}")
        )

    # Navigation
    nav_buttons = []
    if total_pages > 1:
        if page > 1:
            nav_buttons.append(KeyboardButton(text="⬅️ Пред."))
        if page < total_pages:
            nav_buttons.append(KeyboardButton(text="След. ➡️"))

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(KeyboardButton(text="◀️ Назад к выводам"))

    return builder.as_markup(resize_keyboard=True)


def admin_withdrawal_detail_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for viewing a specific withdrawal request details.

    Returns:
        ReplyKeyboardMarkup with action buttons
    """
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="✅ Одобрить"),
        KeyboardButton(text="❌ Отклонить")
    )
    builder.row(
        KeyboardButton(text="◀️ Назад к списку"),
        KeyboardButton(text="👑 Админ-панель")
    )
    return builder.as_markup(resize_keyboard=True)


def withdrawal_confirm_keyboard(withdrawal_id: int, action: str) -> ReplyKeyboardMarkup:
    """Keyboard for confirming withdrawal action."""
    builder = ReplyKeyboardBuilder()
    action_text = "Одобрить" if action == "approve" else "Отклонить"
    builder.row(
        KeyboardButton(text=f"✅ Да, {action_text.lower()} #{withdrawal_id}"),
    )
    builder.row(
        KeyboardButton(text="❌ Нет, отменить"),
    )
    return builder.as_markup(resize_keyboard=True)


def admin_withdrawal_settings_keyboard(
    is_daily_limit_enabled: bool = True,
    auto_withdrawal_enabled: bool = False,
) -> ReplyKeyboardMarkup:
    """
    Admin withdrawal settings keyboard (Reply version).

    Args:
        is_daily_limit_enabled: Whether daily limit is enabled
        auto_withdrawal_enabled: Whether auto-withdrawal is enabled

    Returns:
        ReplyKeyboardMarkup with withdrawal settings options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(KeyboardButton(text="💵 Изм. Мин. Вывод"))
    builder.row(KeyboardButton(text="🛡 Изм. Дневной Лимит"))
    builder.row(KeyboardButton(text="💸 Изм. Комиссию (%)"))

    limit_text = (
        "🔴 Выключить Лимит" if is_daily_limit_enabled
        else "🟢 Включить Лимит"
    )
    builder.row(KeyboardButton(text=limit_text))

    auto_text = (
        "🔴 Выключить Авто-вывод" if auto_withdrawal_enabled
        else "🟢 Включить Авто-вывод"
    )
    builder.row(KeyboardButton(text=auto_text))

    builder.row(
        KeyboardButton(text="◀️ Назад к выводам"),
        KeyboardButton(text="👑 Админ-панель")
    )

    return builder.as_markup(resize_keyboard=True)


def admin_withdrawal_history_pagination_keyboard(
    page: int = 1,
    total_pages: int = 1,
    is_search_mode: bool = False,
) -> ReplyKeyboardMarkup:
    """
    Admin withdrawal history pagination keyboard (Reply version).

    Args:
        page: Current page number
        total_pages: Total number of pages
        is_search_mode: Whether we are in search results mode

    Returns:
        ReplyKeyboardMarkup with pagination and search buttons
    """
    builder = ReplyKeyboardBuilder()

    # Search button
    builder.row(KeyboardButton(text="🔍 Поиск по выводам"))

    # Navigation buttons
    nav_buttons = []
    if page > 1:
        nav_buttons.append(KeyboardButton(text="⬅️ Пред. страница выводов"))
    if page < total_pages:
        nav_buttons.append(
            KeyboardButton(text="Вперёд страница выводов ➡️")
        )

    if nav_buttons:
        builder.row(*nav_buttons)

    # Clear search button if in search mode
    if is_search_mode:
        builder.row(KeyboardButton(text="🗑 Сбросить поиск"))

    builder.row(
        KeyboardButton(text="◀️ Назад"),
        KeyboardButton(text="👑 Админ-панель")
    )

    return builder.as_markup(resize_keyboard=True)
