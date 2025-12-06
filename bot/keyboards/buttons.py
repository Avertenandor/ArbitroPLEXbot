"""
Button text constants.

Centralized button text constants organized by category.
All button texts used in reply keyboards across the bot.

IMPORTANT: This file has been refactored for better organization.
The actual implementations are now in the bot.keyboards.buttons package.
This file maintains backward compatibility by re-exporting all classes.

For new code, you can import directly from the submodules:
    from bot.keyboards.buttons.main_menu import MainMenuButtons
    from bot.keyboards.buttons.admin import AdminButtons
    etc.

Or continue using this file (backward compatible):
    from bot.keyboards.buttons import MainMenuButtons, AdminButtons
"""

# Re-export all button classes from the refactored modules
from bot.keyboards.buttons import (
    # User-facing buttons
    MainMenuButtons,
    DepositButtons,
    WithdrawalButtons,
    WithdrawalSettingsButtons,
    ReferralButtons,
    SettingsButtons,
    ContactButtons,
    NotificationButtons,
    TransactionButtons,
    AuthButtons,
    AppealButtons,
    # Admin buttons
    AdminButtons,
    AdminUserButtons,
    AdminWalletButtons,
    AdminManagementButtons,
    AdminDepositButtons,
    BroadcastButtons,
    BlacklistButtons,
    MasterKeyButtons,
    UserMessagesButtons,
    ROICorridorButtons,
    FinancialReportButtons,
    # Common buttons
    NavigationButtons,
    PaginationButtons,
    ActionButtons,
    SupportButtons,
    InlineButtons,
)

__all__ = [
    # User-facing buttons
    "MainMenuButtons",
    "DepositButtons",
    "WithdrawalButtons",
    "WithdrawalSettingsButtons",
    "ReferralButtons",
    "SettingsButtons",
    "ContactButtons",
    "NotificationButtons",
    "TransactionButtons",
    "AuthButtons",
    "AppealButtons",
    # Admin buttons
    "AdminButtons",
    "AdminUserButtons",
    "AdminWalletButtons",
    "AdminManagementButtons",
    "AdminDepositButtons",
    "BroadcastButtons",
    "BlacklistButtons",
    "MasterKeyButtons",
    "UserMessagesButtons",
    "ROICorridorButtons",
    "FinancialReportButtons",
    # Common buttons
    "NavigationButtons",
    "PaginationButtons",
    "ActionButtons",
    "SupportButtons",
    "InlineButtons",
]
