"""
Button text constants.

Centralized button text constants organized by category.
All button texts used in reply keyboards across the bot.

This module has been refactored into smaller, logically organized submodules:
- main_menu: User main menu buttons
- admin: Admin panel buttons
- admin_deposits: Admin deposit management
- navigation: Navigation and pagination
- actions: Confirmation and action buttons
- support: Support and tickets
- deposits: User deposits
- withdrawals: User withdrawals and settings
- referrals: Referral system
- settings: User settings, contacts, notifications
- transactions: Transaction history
- auth: Authorization and appeals
- broadcast: Admin broadcast
- blacklist: Blacklist management
- master_key: Master key management
- user_messages: User message viewing
- roi: ROI corridor management
- financial: Financial reports
- inline: Inline keyboard buttons

All classes are re-exported here for backward compatibility.
"""

# ============================================================================
# USER-FACING BUTTONS
# ============================================================================

from bot.keyboards.buttons.actions import ActionButtons

# ============================================================================
# ADMIN BUTTONS
# ============================================================================
from bot.keyboards.buttons.admin import (
    AdminButtons,
    AdminManagementButtons,
    AdminUserButtons,
    AdminWalletButtons,
)
from bot.keyboards.buttons.admin_deposits import AdminDepositButtons
from bot.keyboards.buttons.auth import AppealButtons, AuthButtons
from bot.keyboards.buttons.blacklist import BlacklistButtons
from bot.keyboards.buttons.broadcast import BroadcastButtons
from bot.keyboards.buttons.deposits import DepositButtons
from bot.keyboards.buttons.financial import FinancialReportButtons
from bot.keyboards.buttons.inline import InlineButtons
from bot.keyboards.buttons.main_menu import MainMenuButtons
from bot.keyboards.buttons.master_key import MasterKeyButtons

# ============================================================================
# COMMON BUTTONS
# ============================================================================
from bot.keyboards.buttons.navigation import NavigationButtons, PaginationButtons
from bot.keyboards.buttons.referrals import ReferralButtons
from bot.keyboards.buttons.roi import ROICorridorButtons
from bot.keyboards.buttons.settings import (
    ContactButtons,
    NotificationButtons,
    SettingsButtons,
)
from bot.keyboards.buttons.support import SupportButtons
from bot.keyboards.buttons.transactions import TransactionButtons
from bot.keyboards.buttons.user_messages import UserMessagesButtons
from bot.keyboards.buttons.withdrawals import (
    WithdrawalButtons,
    WithdrawalSettingsButtons,
)


# ============================================================================
# PUBLIC API
# ============================================================================

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
