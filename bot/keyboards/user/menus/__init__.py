"""
Menu keyboards module.

This module provides a unified interface to all menu keyboards.
All keyboards are organized into modular files for better maintainability:
- main_menu.py: Main menu and submenu keyboards
- deposit_menu.py: Deposit-related keyboards with levels
- financial_menu.py: Financial operation keyboards
- settings_menu.py: Settings and profile keyboards
- helpers.py: Helper functions and small utility keyboards
- contacts.py: Contact management keyboards
- referral.py: Referral system keyboards

All keyboards are re-exported here for backward compatibility.
"""

# Main menu keyboards
# Deposit menu keyboards
from .deposit_menu import (
    deposit_levels_keyboard,
    deposit_menu_keyboard,
    instructions_keyboard,
)

# Financial menu keyboards
from .financial_menu import (
    balance_menu_keyboard,
    earnings_dashboard_keyboard,
    withdrawal_menu_keyboard,
)

# Helper keyboards and functions
from .helpers import (
    add_navigation_buttons,
    build_level_button_text,
    support_keyboard,
)
from .main_menu import (
    cabinet_submenu_keyboard,
    finances_submenu_keyboard,
    help_submenu_keyboard,
    main_menu_keyboard,
)

# Referral menu keyboards
from .referral import referral_menu_keyboard

# Settings menu keyboards
from .settings_menu import (
    contact_input_keyboard,
    contact_update_menu_keyboard,
    contacts_choice_keyboard,
    notification_settings_reply_keyboard,
    profile_menu_keyboard,
    settings_menu_keyboard,
    wallet_menu_keyboard,
)


# Public exports for backward compatibility
__all__ = [
    # Main menu keyboards
    "main_menu_keyboard",
    "finances_submenu_keyboard",
    "cabinet_submenu_keyboard",
    "help_submenu_keyboard",
    # Deposit menus
    "deposit_menu_keyboard",
    "deposit_levels_keyboard",
    "instructions_keyboard",
    # Financial menus
    "balance_menu_keyboard",
    "withdrawal_menu_keyboard",
    "earnings_dashboard_keyboard",
    # Settings menus
    "settings_menu_keyboard",
    "profile_menu_keyboard",
    "notification_settings_reply_keyboard",
    "wallet_menu_keyboard",
    # Contact menus
    "contact_update_menu_keyboard",
    "contact_input_keyboard",
    "contacts_choice_keyboard",
    # Referral menu
    "referral_menu_keyboard",
    # Support
    "support_keyboard",
    # Helper functions
    "build_level_button_text",
    "add_navigation_buttons",
]
