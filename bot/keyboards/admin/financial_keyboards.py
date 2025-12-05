"""
Financial reporting keyboards for admin panel.

Contains keyboards for viewing financial reports, finpass recovery requests,
and user financial details.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def admin_finpass_request_list_keyboard(
    requests: list,
    page: int = 1,
    total_pages: int = 1,
) -> ReplyKeyboardMarkup:
    """
    Keyboard with finpass recovery request buttons for admin selection.

    Args:
        requests: List of FinpassRecoveryRequest objects
        page: Current page
        total_pages: Total pages

    Returns:
        ReplyKeyboardMarkup with request buttons
    """
    builder = ReplyKeyboardBuilder()

    # Request buttons (2 per row)
    for i in range(0, len(requests), 2):
        row_buttons = []
        # Button 1
        r1 = requests[i]
        # Try to get user label if available (joined) or just ID
        user_label1 = f"User {r1.user_id}"
        if hasattr(r1, 'user') and r1.user:
            if r1.user.username:
                user_label1 = f"@{r1.user.username}"
            elif r1.user.telegram_id:
                user_label1 = f"TG {r1.user.telegram_id}"

        row_buttons.append(KeyboardButton(text=f"🔑 Запрос #{r1.id} {user_label1}"))

        # Button 2 (if exists)
        if i + 1 < len(requests):
            r2 = requests[i + 1]
            user_label2 = f"User {r2.user_id}"
            if hasattr(r2, 'user') and r2.user:
                if r2.user.username:
                    user_label2 = f"@{r2.user.username}"
                elif r2.user.telegram_id:
                    user_label2 = f"TG {r2.user.telegram_id}"
            row_buttons.append(KeyboardButton(text=f"🔑 Запрос #{r2.id} {user_label2}"))

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
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def admin_finpass_request_actions_keyboard() -> ReplyKeyboardMarkup:
    """
    Actions keyboard for a specific finpass recovery request.

    Returns:
        ReplyKeyboardMarkup with actions
    """
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="✅ Одобрить запрос"),
        KeyboardButton(text="❌ Отклонить запрос"),
    )
    builder.row(
        KeyboardButton(text="◀️ Назад к списку"),
        KeyboardButton(text="👑 Админ-панель"),
    )
    return builder.as_markup(resize_keyboard=True)


def admin_financial_list_keyboard(
    users: list,
    page: int = 1,
    total_pages: int = 1,
) -> ReplyKeyboardMarkup:
    """
    Keyboard with users for financial report selection.

    Args:
        users: List of UserFinancialDTO objects
        page: Current page
        total_pages: Total pages

    Returns:
        ReplyKeyboardMarkup
    """
    builder = ReplyKeyboardBuilder()

    for user in users:
        # Truncate if too long, but try to show financial summary
        username = user.username or str(user.telegram_id)
        if len(username) > 15:
            username = username[:12] + "..."

        text = (
            f"👤 {user.id}. {username} | "
            f"+{int(user.total_deposited)} | -{int(user.total_withdrawn)}"
        )
        builder.row(KeyboardButton(text=text))

    # Navigation
    nav_buttons = []
    if total_pages > 1:
        if page > 1:
            nav_buttons.append(KeyboardButton(text="⬅ Предыдущая"))
        if page < total_pages:
            nav_buttons.append(KeyboardButton(text="Следующая ➡"))

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(KeyboardButton(text="👑 Админ-панель"))

    return builder.as_markup(resize_keyboard=True)


def admin_user_financial_keyboard() -> ReplyKeyboardMarkup:
    """
    Actions for a selected user in financial report.

    Returns:
        ReplyKeyboardMarkup
    """
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="💸 История выводов"),
        KeyboardButton(text="📜 История начислений"),
    )
    builder.row(
        KeyboardButton(text="◀️ Назад к списку"),
        KeyboardButton(text="👑 Админ-панель"),
    )
    return builder.as_markup(resize_keyboard=True)


def admin_back_keyboard() -> ReplyKeyboardMarkup:
    """
    Simple back keyboard.

    Returns:
        ReplyKeyboardMarkup
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="◀️ Назад"))
    builder.row(KeyboardButton(text="👑 Админ-панель"))
    return builder.as_markup(resize_keyboard=True)


def admin_user_financial_detail_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for detailed user financial card.

    Returns:
        ReplyKeyboardMarkup with navigation options
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📊 Все депозиты"))
    builder.row(KeyboardButton(text="💸 Все выводы"))
    builder.row(KeyboardButton(text="💳 История кошельков"))
    builder.row(
        KeyboardButton(text="⬅ Назад к списку"),
        KeyboardButton(text="👑 Админ-панель")
    )
    return builder.as_markup(resize_keyboard=True)


def admin_deposits_list_keyboard(
    page: int = 1, total_pages: int = 1
) -> ReplyKeyboardMarkup:
    """
    Keyboard for deposits list with pagination.

    Args:
        page: Current page number
        total_pages: Total number of pages

    Returns:
        ReplyKeyboardMarkup with pagination
    """
    builder = ReplyKeyboardBuilder()

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
        KeyboardButton(text="◀️ К карточке"),
        KeyboardButton(text="👑 Админ-панель")
    )

    return builder.as_markup(resize_keyboard=True)


def admin_withdrawals_list_keyboard(
    page: int = 1, total_pages: int = 1
) -> ReplyKeyboardMarkup:
    """
    Keyboard for withdrawals list with pagination.

    Args:
        page: Current page number
        total_pages: Total number of pages

    Returns:
        ReplyKeyboardMarkup with pagination
    """
    builder = ReplyKeyboardBuilder()

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
        KeyboardButton(text="◀️ К карточке"),
        KeyboardButton(text="👑 Админ-панель")
    )

    return builder.as_markup(resize_keyboard=True)


def admin_wallet_history_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for wallet change history.

    Returns:
        ReplyKeyboardMarkup with back navigation
    """
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="◀️ К карточке"),
        KeyboardButton(text="👑 Админ-панель")
    )
    return builder.as_markup(resize_keyboard=True)
