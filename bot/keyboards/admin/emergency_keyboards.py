"""
Emergency stops keyboards for admin panel.

Contains keyboards for managing emergency stop controls (deposits, withdrawals, ROI).
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def emergency_stops_keyboard(
    deposits_stopped: bool,
    withdrawals_stopped: bool,
    roi_stopped: bool,
) -> ReplyKeyboardMarkup:
    """
    Emergency stops control keyboard with dynamic button states.

    Args:
        deposits_stopped: Whether deposits are currently stopped
        withdrawals_stopped: Whether withdrawals are currently stopped
        roi_stopped: Whether ROI is currently stopped

    Returns:
        ReplyKeyboardMarkup with emergency stop controls
    """
    builder = ReplyKeyboardBuilder()

    # Deposits control button
    deposits_text = (
        "▶️ Запустить депозиты" if deposits_stopped
        else "⏸ Остановить депозиты"
    )
    builder.row(KeyboardButton(text=deposits_text))

    # Withdrawals control button
    withdrawals_text = (
        "▶️ Запустить выводы" if withdrawals_stopped
        else "⏸ Остановить выводы"
    )
    builder.row(KeyboardButton(text=withdrawals_text))

    # ROI control button
    roi_text = "▶️ Запустить ROI" if roi_stopped else "⏸ Остановить ROI"
    builder.row(KeyboardButton(text=roi_text))

    # Refresh status button
    builder.row(KeyboardButton(text="🔄 Обновить статус стопов"))

    # Back button
    builder.row(KeyboardButton(text="◀️ Назад в админку"))

    return builder.as_markup(resize_keyboard=True)
