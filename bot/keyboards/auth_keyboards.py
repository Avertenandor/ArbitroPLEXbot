"""
Auth-related keyboards.

Reply keyboards for authentication, registration, language selection,
and financial password management.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from bot.keyboards.buttons import (
    ActionButtons,
    AuthButtons,
    ContactButtons,
    NavigationButtons,
)

# ============================================================================
# LANGUAGE SELECTION
# ============================================================================


def language_selection_keyboard() -> ReplyKeyboardMarkup:
    """
    Language selection keyboard.

    Shows available language options for user to select.

    Returns:
        ReplyKeyboardMarkup with language selection buttons
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="🇷🇺 Русский"),
        KeyboardButton(text="🇬🇧 English"),
    )
    builder.row(
        KeyboardButton(text=NavigationButtons.BACK),
    )

    return builder.as_markup(resize_keyboard=True)


# ============================================================================
# REGISTRATION KEYBOARDS
# ============================================================================


def registration_password_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for financial password input during registration.

    Returns:
        ReplyKeyboardMarkup with cancel button
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text=NavigationButtons.CANCEL),
    )

    return builder.as_markup(resize_keyboard=True)


def registration_confirm_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for password confirmation during registration.

    Returns:
        ReplyKeyboardMarkup with cancel button
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text=NavigationButtons.CANCEL),
    )

    return builder.as_markup(resize_keyboard=True)


def registration_skip_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard with skip option for optional registration steps.

    Returns:
        ReplyKeyboardMarkup with skip and navigation buttons
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text=ContactButtons.SKIP),
    )
    builder.row(
        KeyboardButton(text=NavigationButtons.BACK),
        KeyboardButton(text=NavigationButtons.HOME),
    )

    return builder.as_markup(resize_keyboard=True)


def contacts_choice_keyboard() -> ReplyKeyboardMarkup:
    """
    Contacts choice keyboard for registration.

    Returns:
        ReplyKeyboardMarkup with contacts choice options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text=ContactButtons.YES_LEAVE_CONTACTS),
    )
    builder.row(
        KeyboardButton(text=ContactButtons.SKIP),
    )

    return builder.as_markup(resize_keyboard=True)


# ============================================================================
# AUTHORIZATION (PAY-TO-USE) KEYBOARDS
# ============================================================================


def auth_wallet_input_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for wallet input during authorization.

    Returns:
        ReplyKeyboardMarkup with cancel button
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=NavigationButtons.CANCEL))
    return builder.as_markup(resize_keyboard=True)


def auth_payment_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for payment confirmation during authorization.

    Returns:
        ReplyKeyboardMarkup with payment confirmation button
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=AuthButtons.I_PAID))
    return builder.as_markup(resize_keyboard=True)


def auth_continue_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard after successful payment - continue to main menu.

    Returns:
        ReplyKeyboardMarkup with continue button
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=AuthButtons.START_WORK))
    return builder.as_markup(resize_keyboard=True)


def auth_rescan_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for deposit rescan option.

    Returns:
        ReplyKeyboardMarkup with rescan and continue buttons
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=AuthButtons.UPDATE_DEPOSIT))
    builder.row(KeyboardButton(text=AuthButtons.CONTINUE_WITHOUT_DEPOSIT))
    return builder.as_markup(resize_keyboard=True)


def auth_retry_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for payment retry.

    Returns:
        ReplyKeyboardMarkup with retry button
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=AuthButtons.CHECK_AGAIN))
    return builder.as_markup(resize_keyboard=True)


def show_password_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard to show password again after registration.

    Returns:
        ReplyKeyboardMarkup with show password button
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=AuthButtons.SHOW_PASSWORD_AGAIN))
    builder.row(KeyboardButton(text=NavigationButtons.MAIN_MENU))
    return builder.as_markup(resize_keyboard=True)


# ============================================================================
# FINANCIAL PASSWORD KEYBOARDS
# ============================================================================


def finpass_input_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for financial password input with cancel button.

    Used during withdrawal operations to request financial password.

    Returns:
        ReplyKeyboardMarkup with cancel option
    """
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="❌ Отменить вывод"),
    )
    return builder.as_markup(resize_keyboard=True)


def finpass_recovery_keyboard() -> ReplyKeyboardMarkup:
    """
    Financial password recovery keyboard.

    Returns:
        ReplyKeyboardMarkup with recovery options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text=NavigationButtons.CANCEL),
    )
    builder.row(
        KeyboardButton(text=NavigationButtons.MAIN_MENU),
    )

    return builder.as_markup(resize_keyboard=True)


def finpass_recovery_confirm_keyboard() -> ReplyKeyboardMarkup:
    """
    Financial password recovery confirmation keyboard.

    Returns:
        ReplyKeyboardMarkup with confirm/cancel buttons
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text=ActionButtons.SEND_REQUEST),
    )
    builder.row(
        KeyboardButton(text=ActionButtons.CANCEL_ACTION),
    )

    return builder.as_markup(resize_keyboard=True)
