"""
User-related reply keyboards (LEGACY).

IMPORTANT: This module has been refactored into a modular structure.
All keyboards are now located in the bot.keyboards.user package:
  - bot.keyboards.user.main_menu: Main menu keyboard
  - bot.keyboards.user.menus: Basic menu keyboards (balance, deposit, withdrawal, etc.)
  - bot.keyboards.user.financial: Financial operation keyboards (finpass, etc.)
  - bot.keyboards.user.history: Transaction history and list keyboards
  - bot.keyboards.user.auth: Authorization/pay-to-use keyboards
  - bot.keyboards.user.inquiry: User inquiry keyboards
  - bot.keyboards.user.utility: Utility keyboards (confirmation, cancel)

This file is maintained for backward compatibility only.
All imports are re-exported from the new modular structure.

Migration Guide:
---------------
Old import:
    from bot.keyboards.user_keyboards import main_menu_reply_keyboard

New import (recommended):
    from bot.keyboards.user import main_menu_reply_keyboard

Or:
    from bot.keyboards import main_menu_reply_keyboard
"""

# Re-export all keyboards from new modular structure for backward compatibility
from bot.keyboards.user import (
    # Main menu
    main_menu_reply_keyboard,
    # Basic menus
    balance_menu_keyboard,
    contact_input_keyboard,
    contact_update_menu_keyboard,
    contacts_choice_keyboard,
    deposit_menu_keyboard,
    notification_settings_reply_keyboard,
    profile_menu_keyboard,
    referral_menu_keyboard,
    settings_menu_keyboard,
    support_keyboard,
    wallet_menu_keyboard,
    withdrawal_menu_keyboard,
    # Financial keyboards
    finpass_input_keyboard,
    finpass_recovery_confirm_keyboard,
    finpass_recovery_keyboard,
    show_password_keyboard,
    # History keyboards
    referral_list_keyboard,
    transaction_history_keyboard,
    transaction_history_type_keyboard,
    withdrawal_history_keyboard,
    # Authorization keyboards
    auth_continue_keyboard,
    auth_payment_keyboard,
    auth_rescan_keyboard,
    auth_retry_keyboard,
    auth_wallet_input_keyboard,
    # Inquiry keyboards
    inquiry_dialog_keyboard,
    inquiry_history_keyboard,
    inquiry_input_keyboard,
    inquiry_waiting_keyboard,
    # Utility keyboards
    cancel_keyboard,
    confirmation_keyboard,
)

__all__ = [
    # Main menu
    "main_menu_reply_keyboard",
    # Basic menus
    "balance_menu_keyboard",
    "contact_input_keyboard",
    "contact_update_menu_keyboard",
    "contacts_choice_keyboard",
    "deposit_menu_keyboard",
    "notification_settings_reply_keyboard",
    "profile_menu_keyboard",
    "referral_menu_keyboard",
    "settings_menu_keyboard",
    "support_keyboard",
    "wallet_menu_keyboard",
    "withdrawal_menu_keyboard",
    # Financial keyboards
    "finpass_input_keyboard",
    "finpass_recovery_confirm_keyboard",
    "finpass_recovery_keyboard",
    "show_password_keyboard",
    # History keyboards
    "referral_list_keyboard",
    "transaction_history_keyboard",
    "transaction_history_type_keyboard",
    "withdrawal_history_keyboard",
    # Authorization keyboards
    "auth_continue_keyboard",
    "auth_payment_keyboard",
    "auth_rescan_keyboard",
    "auth_retry_keyboard",
    "auth_wallet_input_keyboard",
    # Inquiry keyboards
    "inquiry_dialog_keyboard",
    "inquiry_history_keyboard",
    "inquiry_input_keyboard",
    "inquiry_waiting_keyboard",
    # Utility keyboards
    "cancel_keyboard",
    "confirmation_keyboard",
]
