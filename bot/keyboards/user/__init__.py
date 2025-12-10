"""
User keyboards package.

This package contains all user-facing keyboard builders, organized into modules:

Module Structure:
-----------------
- main_menu.py: Main menu keyboard with conditional buttons (admin, blocked users, etc.)
- menus.py: Basic menu keyboards (balance, deposit, withdrawal, referral, settings, etc.)
- financial.py: Financial operations keyboards (finpass, password recovery)
- history.py: Transaction history, referral lists, withdrawal history
- auth.py: Authorization/pay-to-use keyboards
- inquiry.py: User inquiry (questions to admins) keyboards
- utility.py: Simple utility keyboards (confirmation, cancel)

Usage:
------
All keyboards can be imported directly from this package:
    from bot.keyboards.user import main_menu_reply_keyboard, deposit_menu_keyboard

For backward compatibility, all keyboards are also re-exported from bot.keyboards module.
"""

# Main menu
# Authorization keyboards
from bot.keyboards.user.auth import (
    auth_continue_keyboard,
    auth_payment_keyboard,
    auth_rescan_keyboard,
    auth_retry_keyboard,
    auth_wallet_input_keyboard,
)

# Financial keyboards
from bot.keyboards.user.financial import (
    finpass_input_keyboard,
    finpass_recovery_confirm_keyboard,
    finpass_recovery_keyboard,
    show_password_keyboard,
)

# History keyboards
from bot.keyboards.user.history import (
    referral_list_keyboard,
    transaction_history_keyboard,
    transaction_history_type_keyboard,
    withdrawal_history_keyboard,
)

# Inquiry keyboards
from bot.keyboards.user.inquiry import (
    inquiry_dialog_keyboard,
    inquiry_history_keyboard,
    inquiry_input_keyboard,
    inquiry_waiting_keyboard,
)
from bot.keyboards.user.main_menu import main_menu_reply_keyboard

# Basic menus
from bot.keyboards.user.menus import (
    balance_menu_keyboard,
    cabinet_submenu_keyboard,
    contact_input_keyboard,
    contact_update_menu_keyboard,
    contacts_choice_keyboard,
    deposit_levels_keyboard,
    deposit_menu_keyboard,
    earnings_dashboard_keyboard,
    finances_submenu_keyboard,
    help_submenu_keyboard,
    instructions_keyboard,
    main_menu_keyboard,
    notification_settings_reply_keyboard,
    profile_menu_keyboard,
    referral_menu_keyboard,
    settings_menu_keyboard,
    support_keyboard,
    wallet_menu_keyboard,
    withdrawal_menu_keyboard,
)

# Utility keyboards
from bot.keyboards.user.utility import cancel_keyboard, confirmation_keyboard


__all__ = [
    # Main menu
    "main_menu_reply_keyboard",
    # Basic menus
    "balance_menu_keyboard",
    "cabinet_submenu_keyboard",
    "contact_input_keyboard",
    "contact_update_menu_keyboard",
    "contacts_choice_keyboard",
    "deposit_levels_keyboard",
    "deposit_menu_keyboard",
    "earnings_dashboard_keyboard",
    "finances_submenu_keyboard",
    "help_submenu_keyboard",
    "instructions_keyboard",
    "main_menu_keyboard",
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
