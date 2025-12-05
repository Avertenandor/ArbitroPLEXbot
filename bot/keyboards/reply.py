"""
Reply keyboards facade module.

DEPRECATION NOTICE:
This module is maintained for backwards compatibility only.
New code should import directly from the specific modules:
- bot.keyboards.user_keyboards for user-facing keyboards
- bot.keyboards.admin_keyboards for admin keyboards
- bot.keyboards.auth_keyboards for authentication keyboards
- bot.keyboards.buttons for button text constants
- bot.keyboards.builders for keyboard builder utilities

This facade will be removed in a future version.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# Admin keyboards
from bot.keyboards.admin_keyboards import (
    admin_back_keyboard,
    admin_blacklist_keyboard,
    admin_broadcast_button_choice_keyboard,
    admin_broadcast_cancel_keyboard,
    admin_broadcast_keyboard,
    admin_deposit_level_actions_keyboard,
    admin_deposit_levels_keyboard,
    admin_deposit_management_keyboard,
    admin_deposit_settings_keyboard,
    admin_deposits_list_keyboard,
    admin_financial_list_keyboard,
    admin_finpass_request_actions_keyboard,
    admin_finpass_request_list_keyboard,
    admin_keyboard,
    admin_management_keyboard,
    admin_roi_applies_to_keyboard,
    admin_roi_confirmation_keyboard,
    admin_roi_corridor_menu_keyboard,
    admin_roi_level_select_keyboard,
    admin_roi_mode_select_keyboard,
    admin_support_keyboard,
    admin_support_ticket_keyboard,
    admin_ticket_list_keyboard,
    admin_user_financial_detail_keyboard,
    admin_user_financial_keyboard,
    admin_user_list_keyboard,
    admin_user_profile_keyboard,
    admin_users_keyboard,
    admin_wallet_history_keyboard,
    admin_wallet_keyboard,
    admin_withdrawal_detail_keyboard,
    admin_withdrawal_history_pagination_keyboard,
    admin_withdrawal_settings_keyboard,
    admin_withdrawals_keyboard,
    admin_withdrawals_list_keyboard,
    get_admin_keyboard_from_data,
    withdrawal_confirm_keyboard,
    withdrawal_list_keyboard,
)

# Auth keyboards
from bot.keyboards.auth_keyboards import (
    auth_continue_keyboard,
    auth_payment_keyboard,
    auth_rescan_keyboard,
    auth_retry_keyboard,
    auth_wallet_input_keyboard,
    language_selection_keyboard,
    registration_confirm_keyboard,
    registration_password_keyboard,
    registration_skip_keyboard,
)

# ============================================================================
# IMPORTS FROM MODULAR KEYBOARDS
# ============================================================================
# User keyboards - Import from new modular structure
from bot.keyboards.user import (
    balance_menu_keyboard,
    cancel_keyboard,
    confirmation_keyboard,
    contact_input_keyboard,
    contact_update_menu_keyboard,
    contacts_choice_keyboard,
    deposit_menu_keyboard,
    finpass_input_keyboard,
    finpass_recovery_confirm_keyboard,
    finpass_recovery_keyboard,
    main_menu_reply_keyboard,
    notification_settings_reply_keyboard,
    profile_menu_keyboard,
    referral_list_keyboard,
    referral_menu_keyboard,
    settings_menu_keyboard,
    show_password_keyboard,
    support_keyboard,
    transaction_history_keyboard,
    transaction_history_type_keyboard,
    wallet_menu_keyboard,
    withdrawal_history_keyboard,
    withdrawal_menu_keyboard,
)

# ============================================================================
# BACKWARDS COMPATIBILITY ALIASES
# These functions were renamed in the new modules
# ============================================================================

# Renamed: deposit_keyboard → deposit_menu_keyboard
deposit_keyboard = deposit_menu_keyboard

# Renamed: withdrawal_keyboard → withdrawal_menu_keyboard
withdrawal_keyboard = withdrawal_menu_keyboard

# Renamed: referral_keyboard → referral_menu_keyboard
referral_keyboard = referral_menu_keyboard

# Renamed: settings_keyboard → settings_menu_keyboard
settings_keyboard = settings_menu_keyboard

# Renamed: profile_keyboard → profile_menu_keyboard
profile_keyboard = profile_menu_keyboard


# ============================================================================
# FUNCTIONS NOT YET EXTRACTED TO NEW MODULES
# These remain here until they are moved to appropriate modules
# ============================================================================


def master_key_management_reply_keyboard() -> ReplyKeyboardMarkup:
    """
    Master key management keyboard (reply).

    Returns:
        ReplyKeyboardMarkup with master key management options
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🔍 Показать текущий ключ"))
    builder.row(KeyboardButton(text="🔄 Сгенерировать новый ключ"))
    builder.row(KeyboardButton(text="◀️ Главное меню"))
    return builder.as_markup(resize_keyboard=True)


def user_messages_navigation_keyboard(
    has_prev: bool,
    has_next: bool,
    is_super_admin: bool = False,
) -> ReplyKeyboardMarkup:
    """
    User messages navigation keyboard (reply).

    Args:
        has_prev: Whether there is a previous page
        has_next: Whether there is a next page
        is_super_admin: Whether user is super admin (shows delete button)

    Returns:
        ReplyKeyboardMarkup with navigation buttons
    """
    builder = ReplyKeyboardBuilder()

    # Navigation row
    nav_buttons = []
    if has_prev:
        nav_buttons.append(KeyboardButton(text="⬅️ Предыдущая страница"))
    if has_next:
        nav_buttons.append(KeyboardButton(text="➡️ Следующая страница"))

    if nav_buttons:
        builder.row(*nav_buttons)

    # Action buttons
    builder.row(
        KeyboardButton(text="🔍 Другой пользователь"),
        KeyboardButton(text="📊 Статистика"),
    )

    # Delete button (only for super admin)
    if is_super_admin:
        builder.row(KeyboardButton(text="🗑 Удалить все сообщения"))

    # Back button
    builder.row(KeyboardButton(text="◀️ Назад в админ-панель"))

    return builder.as_markup(resize_keyboard=True)


# ============================================================================
# RE-EXPORTS FOR BACKWARDS COMPATIBILITY
# All functions are now exported from their respective modules
# ============================================================================

__all__ = [
    # Main user keyboards
    "main_menu_reply_keyboard",
    "balance_menu_keyboard",
    "deposit_menu_keyboard",
    "deposit_keyboard",  # Alias for deposit_menu_keyboard
    "withdrawal_menu_keyboard",
    "withdrawal_keyboard",  # Alias for withdrawal_menu_keyboard
    "referral_menu_keyboard",
    "referral_keyboard",  # Alias for referral_menu_keyboard
    "settings_menu_keyboard",
    "settings_keyboard",  # Alias for settings_menu_keyboard
    "profile_menu_keyboard",
    "profile_keyboard",  # Alias for profile_menu_keyboard
    "contact_update_menu_keyboard",
    "contact_input_keyboard",
    "wallet_menu_keyboard",
    "support_keyboard",
    "finpass_input_keyboard",
    "finpass_recovery_keyboard",
    "finpass_recovery_confirm_keyboard",
    "notification_settings_reply_keyboard",
    "contacts_choice_keyboard",
    "transaction_history_type_keyboard",
    "transaction_history_keyboard",
    "referral_list_keyboard",
    "withdrawal_history_keyboard",
    "show_password_keyboard",
    "confirmation_keyboard",
    "cancel_keyboard",
    # Admin keyboards
    "get_admin_keyboard_from_data",
    "admin_keyboard",
    "admin_users_keyboard",
    "admin_withdrawals_keyboard",
    "withdrawal_list_keyboard",
    "admin_withdrawal_detail_keyboard",
    "withdrawal_confirm_keyboard",
    "admin_wallet_keyboard",
    "admin_broadcast_button_choice_keyboard",
    "admin_broadcast_cancel_keyboard",
    "admin_broadcast_keyboard",
    "admin_support_keyboard",
    "admin_support_ticket_keyboard",
    "admin_blacklist_keyboard",
    "admin_management_keyboard",
    "admin_deposit_settings_keyboard",
    "admin_deposit_management_keyboard",
    "admin_deposit_levels_keyboard",
    "admin_deposit_level_actions_keyboard",
    "admin_roi_corridor_menu_keyboard",
    "admin_roi_level_select_keyboard",
    "admin_roi_mode_select_keyboard",
    "admin_roi_applies_to_keyboard",
    "admin_roi_confirmation_keyboard",
    "admin_ticket_list_keyboard",
    "admin_user_list_keyboard",
    "admin_user_profile_keyboard",
    "admin_finpass_request_list_keyboard",
    "admin_finpass_request_actions_keyboard",
    "admin_financial_list_keyboard",
    "admin_user_financial_keyboard",
    "admin_back_keyboard",
    "admin_user_financial_detail_keyboard",
    "admin_deposits_list_keyboard",
    "admin_withdrawals_list_keyboard",
    "admin_wallet_history_keyboard",
    "admin_withdrawal_settings_keyboard",
    "admin_withdrawal_history_pagination_keyboard",
    # Auth keyboards
    "language_selection_keyboard",
    "registration_password_keyboard",
    "registration_confirm_keyboard",
    "registration_skip_keyboard",
    "auth_wallet_input_keyboard",
    "auth_payment_keyboard",
    "auth_continue_keyboard",
    "auth_rescan_keyboard",
    "auth_retry_keyboard",
    # Functions not yet extracted
    "master_key_management_reply_keyboard",
    "user_messages_navigation_keyboard",
]
