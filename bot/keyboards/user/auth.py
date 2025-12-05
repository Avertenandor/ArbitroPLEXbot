"""
Authorization (Pay-to-use) keyboards module.

This module contains keyboards for user authorization and payment flow:
- Wallet input
- Payment confirmation
- Deposit rescan
- Payment retry
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def auth_wallet_input_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for wallet input during authorization.

    Returns:
        ReplyKeyboardMarkup with cancel button
    """
    builder = ReplyKeyboardBuilder()

    builder.row(KeyboardButton(text="❌ Отмена"))

    return builder.as_markup(resize_keyboard=True)


def auth_payment_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for payment confirmation during authorization.

    Returns:
        ReplyKeyboardMarkup with payment confirmation button
    """
    builder = ReplyKeyboardBuilder()

    builder.row(KeyboardButton(text="✅ Я оплатил"))

    return builder.as_markup(resize_keyboard=True)


def auth_continue_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard after successful payment - continue to main menu.

    Returns:
        ReplyKeyboardMarkup with continue button
    """
    builder = ReplyKeyboardBuilder()

    builder.row(KeyboardButton(text="🚀 Начать работу"))

    return builder.as_markup(resize_keyboard=True)


def auth_rescan_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for deposit rescan option.

    Returns:
        ReplyKeyboardMarkup with rescan and continue buttons
    """
    builder = ReplyKeyboardBuilder()

    builder.row(KeyboardButton(text="🔄 Обновить депозит"))
    builder.row(KeyboardButton(text="🚀 Продолжить (без депозита)"))

    return builder.as_markup(resize_keyboard=True)


def auth_retry_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for payment retry.

    Returns:
        ReplyKeyboardMarkup with retry button
    """
    builder = ReplyKeyboardBuilder()

    builder.row(KeyboardButton(text="🔄 Проверить снова"))

    return builder.as_markup(resize_keyboard=True)
