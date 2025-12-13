"""
Inline keyboards for deposit status and other interactive elements.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def deposit_status_keyboard(deposit_id: int) -> InlineKeyboardMarkup:
    """
    Keyboard for deposit status view.

    Args:
        deposit_id: Deposit ID

    Returns:
        InlineKeyboardMarkup with refresh option
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🔄 Обновить статус",
            callback_data=f"refresh_deposit_{deposit_id}"
        )
    )

    return builder.as_markup()


def admin_blockchain_keyboard(
    active_provider: str,
    is_auto_switch: bool
) -> InlineKeyboardMarkup:
    """
    Keyboard for blockchain settings management.

    NOTE: This is kept for backward compatibility.
    The new implementation uses reply keyboards in blockchain_keyboards.py
    """
    builder = InlineKeyboardBuilder()

    qn_text = "✅ QuickNode" if active_provider == "quicknode" else "QuickNode"
    nr_text = "✅ NodeReal" if active_provider == "nodereal" else "NodeReal"

    builder.row(
        InlineKeyboardButton(text=qn_text, callback_data="blockchain_set_quicknode"),
        InlineKeyboardButton(text=nr_text, callback_data="blockchain_set_nodereal"),
    )

    auto_text = (
        "✅ Авто-смена ВКЛ" if is_auto_switch
        else "❌ Авто-смена ВЫКЛ"
    )
    builder.row(
        InlineKeyboardButton(text=auto_text, callback_data="blockchain_toggle_auto")
    )

    builder.row(
        InlineKeyboardButton(
            text="🔄 Обновить статус",
            callback_data="blockchain_refresh"
        )
    )

    return builder.as_markup()


def finpass_recovery_actions_keyboard(request_id: int) -> InlineKeyboardMarkup:
    """
    Actions for finpass recovery request.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Одобрить",
            callback_data=f"approve_recovery_{request_id}"
        ),
        InlineKeyboardButton(
            text="❌ Отклонить",
            callback_data=f"reject_recovery_{request_id}"
        ),
    )
    return builder.as_markup()
