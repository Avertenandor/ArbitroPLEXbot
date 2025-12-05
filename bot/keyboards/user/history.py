"""
History and listing keyboards module.

This module contains keyboards for viewing transaction history,
referral lists, withdrawal history, and other historical data.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def transaction_history_type_keyboard() -> ReplyKeyboardMarkup:
    """
    Transaction history type selection keyboard.

    Returns:
        ReplyKeyboardMarkup with transaction type buttons
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="🔄 Внутренние транзакции"),
        KeyboardButton(text="🔗 Транзакции в блокчейне"),
    )
    builder.row(
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def transaction_history_keyboard(
    current_filter: str | None = None,
    has_prev: bool = False,
    has_next: bool = False,
) -> ReplyKeyboardMarkup:
    """
    Transaction history keyboard with filters and pagination.

    Args:
        current_filter: Current filter type (all/deposit/withdrawal/referral)
        has_prev: Whether there is a previous page
        has_next: Whether there is a next page

    Returns:
        ReplyKeyboardMarkup with filter and navigation options
    """
    builder = ReplyKeyboardBuilder()

    # Filter buttons
    builder.row(
        KeyboardButton(text="📊 Все транзакции"),
    )
    builder.row(
        KeyboardButton(text="💰 Депозиты"),
        KeyboardButton(text="💸 Выводы"),
    )
    builder.row(
        KeyboardButton(text="🎁 Реферальные"),
    )

    # Export button
    builder.row(
        KeyboardButton(text="📥 Скачать отчет (Excel)"),
    )

    # Navigation buttons
    nav_buttons = []
    if has_prev:
        nav_buttons.append(KeyboardButton(text="⬅ Предыдущая страница"))
    if has_next:
        nav_buttons.append(KeyboardButton(text="➡ Следующая страница"))

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(
        KeyboardButton(text="◀️ Назад"),
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def referral_list_keyboard(
    level: int = 1,
    page: int = 1,
    total_pages: int = 1,
) -> ReplyKeyboardMarkup:
    """
    Referral list keyboard with level selection and pagination.

    Args:
        level: Current referral level (1-3)
        page: Current page number
        total_pages: Total number of pages

    Returns:
        ReplyKeyboardMarkup with level selection and navigation options
    """
    builder = ReplyKeyboardBuilder()

    # Level selection buttons
    builder.row(
        KeyboardButton(text="📊 Уровень 1"),
        KeyboardButton(text="📊 Уровень 2"),
        KeyboardButton(text="📊 Уровень 3"),
    )

    # Navigation buttons (only if more than one page)
    if total_pages > 1:
        nav_buttons = []
        if page > 1:
            nav_buttons.append(KeyboardButton(text="⬅ Предыдущая страница"))
        if page < total_pages:
            nav_buttons.append(KeyboardButton(text="➡ Следующая страница"))

        if nav_buttons:
            builder.row(*nav_buttons)

    builder.row(
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def withdrawal_history_keyboard(
    page: int = 1,
    total_pages: int = 1,
    has_withdrawals: bool = True,
) -> ReplyKeyboardMarkup:
    """
    Withdrawal history keyboard with pagination.

    Args:
        page: Current page number
        total_pages: Total number of pages
        has_withdrawals: Whether there are any withdrawals

    Returns:
        ReplyKeyboardMarkup with navigation options
    """
    builder = ReplyKeyboardBuilder()

    # Navigation buttons (only if more than one page and has withdrawals)
    if has_withdrawals and total_pages > 1:
        nav_buttons = []
        if page > 1:
            nav_buttons.append(KeyboardButton(text="⬅ Предыдущая страница выводов"))
        if page < total_pages:
            nav_buttons.append(KeyboardButton(text="➡ Следующая страница выводов"))

        if nav_buttons:
            builder.row(*nav_buttons)

    builder.row(
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)
