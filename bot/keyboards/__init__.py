"""
Keyboards.

Telegram keyboards (reply and inline).

This module exports all keyboard components:
- Button classes: Centralized button text constants
- Builder classes: Fluent keyboard builders
- Keyboard functions: Pre-built keyboard factories
"""

# ============================================================================
# BUTTON CLASSES
# ============================================================================

# ============================================================================
# ADMIN KEYBOARDS
# ============================================================================
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

# ============================================================================
# AUTH KEYBOARDS
# ============================================================================
from bot.keyboards.auth_keyboards import (
    auth_continue_keyboard,
    auth_payment_keyboard,
    auth_rescan_keyboard,
    auth_retry_keyboard,
    auth_wallet_input_keyboard,
    contacts_choice_keyboard,
    finpass_input_keyboard,
    finpass_recovery_confirm_keyboard,
    finpass_recovery_keyboard,
    language_selection_keyboard,
    registration_confirm_keyboard,
    registration_password_keyboard,
    registration_skip_keyboard,
    show_password_keyboard,
)

# ============================================================================
# BUILDER CLASSES AND UTILITIES
# ============================================================================
from bot.keyboards.builders import (
    InlineKeyboardBuilder,
    ReplyKeyboardBuilder,
    quick_reply_keyboard,
)
from bot.keyboards.buttons import (
    ActionButtons,
    AdminButtons,
    AdminDepositButtons,
    AdminManagementButtons,
    AdminUserButtons,
    AdminWalletButtons,
    AppealButtons,
    AuthButtons,
    BlacklistButtons,
    BroadcastButtons,
    ContactButtons,
    DepositButtons,
    FinancialReportButtons,
    InlineButtons,
    MainMenuButtons,
    MasterKeyButtons,
    NavigationButtons,
    NotificationButtons,
    PaginationButtons,
    ReferralButtons,
    ROICorridorButtons,
    SettingsButtons,
    SupportButtons,
    TransactionButtons,
    UserMessagesButtons,
    WithdrawalButtons,
    WithdrawalSettingsButtons,
)

# ============================================================================
# USER KEYBOARDS
# ============================================================================
# Import from the new modular structure in bot.keyboards.user package
from bot.keyboards.user import (
    auth_continue_keyboard,
    auth_payment_keyboard,
    auth_rescan_keyboard,
    auth_retry_keyboard,
    auth_wallet_input_keyboard,
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
    inquiry_dialog_keyboard,
    inquiry_history_keyboard,
    inquiry_input_keyboard,
    inquiry_waiting_keyboard,
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
# BACKWARDS COMPATIBILITY (Legacy imports)
# ============================================================================

# Keep legacy naming for backwards compatibility
support_reply_keyboard = support_keyboard

# ============================================================================
# PUBLIC API
# ============================================================================

__all__ = [
    # ========================================================================
    # BUTTON CLASSES
    # ========================================================================
    "ActionButtons",
    "AdminButtons",
    "AdminDepositButtons",
    "AdminManagementButtons",
    "AdminUserButtons",
    "AdminWalletButtons",
    "AppealButtons",
    "AuthButtons",
    "BlacklistButtons",
    "BroadcastButtons",
    "ContactButtons",
    "DepositButtons",
    "FinancialReportButtons",
    "InlineButtons",
    "MainMenuButtons",
    "MasterKeyButtons",
    "NavigationButtons",
    "NotificationButtons",
    "PaginationButtons",
    "ReferralButtons",
    "ROICorridorButtons",
    "SettingsButtons",
    "SupportButtons",
    "TransactionButtons",
    "UserMessagesButtons",
    "WithdrawalButtons",
    "WithdrawalSettingsButtons",
    # ========================================================================
    # BUILDER CLASSES
    # ========================================================================
    "ReplyKeyboardBuilder",
    "InlineKeyboardBuilder",
    "quick_reply_keyboard",
    # ========================================================================
    # USER KEYBOARDS
    # ========================================================================
    "main_menu_reply_keyboard",
    "balance_menu_keyboard",
    "deposit_menu_keyboard",
    "withdrawal_menu_keyboard",
    "referral_menu_keyboard",
    "settings_menu_keyboard",
    "profile_menu_keyboard",
    "contact_update_menu_keyboard",
    "contact_input_keyboard",
    "wallet_menu_keyboard",
    "support_keyboard",
    "notification_settings_reply_keyboard",
    "transaction_history_type_keyboard",
    "transaction_history_keyboard",
    "referral_list_keyboard",
    "withdrawal_history_keyboard",
    "confirmation_keyboard",
    "cancel_keyboard",
    # ========================================================================
    # ADMIN KEYBOARDS
    # ========================================================================
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
    # ========================================================================
    # AUTH KEYBOARDS
    # ========================================================================
    "language_selection_keyboard",
    "registration_password_keyboard",
    "registration_confirm_keyboard",
    "registration_skip_keyboard",
    "contacts_choice_keyboard",
    "auth_wallet_input_keyboard",
    "auth_payment_keyboard",
    "auth_continue_keyboard",
    "auth_rescan_keyboard",
    "auth_retry_keyboard",
    "show_password_keyboard",
    "finpass_input_keyboard",
    "finpass_recovery_keyboard",
    "finpass_recovery_confirm_keyboard",
    # ========================================================================
    # INQUIRY KEYBOARDS
    # ========================================================================
    "inquiry_input_keyboard",
    "inquiry_dialog_keyboard",
    "inquiry_waiting_keyboard",
    "inquiry_history_keyboard",
    # ========================================================================
    # LEGACY / BACKWARDS COMPATIBILITY
    # ========================================================================
    "support_reply_keyboard",
]
