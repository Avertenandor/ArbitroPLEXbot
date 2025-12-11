"""
Keyboard definitions for Bonus Management V2.

Contains all keyboard layouts for bonus management interface:
- Main menu with role-based permissions
- Quick amount selection
- Reason templates
- Confirmation keyboards
- Bonus details actions
"""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from .constants import BONUS_REASON_TEMPLATES, QUICK_AMOUNTS, ROLE_PERMISSIONS


def bonus_main_menu_keyboard(role: str) -> ReplyKeyboardMarkup:
    """
    Главное меню бонусов с учётом роли.

    Модератор: только просмотр
    Админ: просмотр + начисление
    Старший админ: + отмена своих
    Супер-админ: полный доступ
    """
    buttons = []
    permissions = ROLE_PERMISSIONS.get(
        role,
        {"can_grant": False, "can_view": False, "can_cancel_any": False, "can_cancel_own": False},
    )

    # Все роли могут видеть статистику и историю
    buttons.append(
        [
            KeyboardButton(text="📊 Статистика"),
            KeyboardButton(text="📋 История"),
        ]
    )

    # Админы и выше могут начислять
    if permissions["can_grant"]:
        buttons.append([KeyboardButton(text="➕ Начислить бонус")])

    # Поиск доступен всем
    buttons.append(
        [
            KeyboardButton(text="🔍 Найти пользователя"),
            KeyboardButton(text="📑 Мои начисления"),
        ]
    )

    # Супер-админ может отменять бонусы
    if permissions["can_cancel_any"]:
        buttons.append([KeyboardButton(text="⚠️ Отмена бонусов")])

    buttons.append([KeyboardButton(text="◀️ Назад в админку")])

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def amount_quick_select_keyboard() -> ReplyKeyboardMarkup:
    """Быстрый выбор суммы."""
    buttons = [
        [
            KeyboardButton(text="10 USDT"),
            KeyboardButton(text="5 USDT"),
            KeyboardButton(text="50 USDT"),
        ],
        [
            KeyboardButton(text="100 USDT"),
            KeyboardButton(text="30 USDT"),
            KeyboardButton(text="70 USDT"),
        ],
        [KeyboardButton(text="💵 Ввести сумму вручную")],
        [KeyboardButton(text="❌ Отмена")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def reason_templates_keyboard() -> InlineKeyboardMarkup:
    """Шаблоны причин для быстрого выбора."""
    buttons = []
    for idx, (emoji_name, reason) in enumerate(BONUS_REASON_TEMPLATES):
        # Use index instead of full text to avoid 64-byte callback_data limit
        callback = f"bonus_reason:{idx}" if reason else "bonus_reason:custom"
        buttons.append([InlineKeyboardButton(text=emoji_name, callback_data=callback)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_bonus_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение начисления."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Начислить", callback_data="bonus_do_grant"),
                InlineKeyboardButton(text="✏️ Изменить", callback_data="bonus_edit"),
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="bonus_cancel_grant")],
        ]
    )


def bonus_details_keyboard(bonus_id: int, can_cancel: bool) -> InlineKeyboardMarkup:
    """Клавиатура деталей бонуса."""
    buttons = []

    if can_cancel:
        buttons.append([InlineKeyboardButton(text="⚠️ Отменить бонус", callback_data=f"bonus_cancel:{bonus_id}")])

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="bonus_back_to_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def cancel_keyboard() -> ReplyKeyboardMarkup:
    """Кнопка отмены."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
    )
