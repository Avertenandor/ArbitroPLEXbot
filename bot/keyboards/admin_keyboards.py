"""
Admin keyboards module - Backward Compatibility Wrapper.

REFACTORED: This module has been refactored into smaller, well-organized modules
located in bot/keyboards/admin/. This file now serves as a backward compatibility
wrapper to ensure existing imports continue to work.

New modular structure:
- bot/keyboards/admin/main_keyboards.py - Main admin panel keyboard
- bot/keyboards/admin/user_keyboards.py - User management keyboards
- bot/keyboards/admin/withdrawal_keyboards.py - Withdrawal management keyboards
- bot/keyboards/admin/wallet_keyboards.py - Wallet management keyboards
- bot/keyboards/admin/broadcast_keyboards.py - Broadcast keyboards
- bot/keyboards/admin/support_keyboards.py - Support ticket keyboards
- bot/keyboards/admin/blacklist_keyboards.py - Blacklist management keyboards
- bot/keyboards/admin/admin_management_keyboards.py - Admin management keyboards
- bot/keyboards/admin/deposit_keyboards.py - Deposit management keyboards
- bot/keyboards/admin/financial_keyboards.py - Financial reporting keyboards
- bot/keyboards/admin/inquiry_keyboards.py - User inquiry keyboards

For new code, prefer importing directly from bot.keyboards.admin or specific modules.
Example:
    from bot.keyboards.admin import admin_keyboard
    from bot.keyboards.admin.user_keyboards import admin_users_keyboard
"""

# Re-export all functions from the modular structure for backward compatibility
from bot.keyboards.admin import (
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
    admin_inquiry_detail_keyboard,
    admin_inquiry_list_keyboard,
    admin_inquiry_menu_keyboard,
    admin_inquiry_response_keyboard,
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
    admin_bonus_keyboard,
    admin_cancel_keyboard,
    get_admin_keyboard_from_data,
    withdrawal_confirm_keyboard,
    withdrawal_list_keyboard,
)

# Export all for backward compatibility
__all__ = [
    "admin_back_keyboard",
    "admin_blacklist_keyboard",
    "admin_broadcast_button_choice_keyboard",
    "admin_broadcast_cancel_keyboard",
    "admin_broadcast_keyboard",
    "admin_deposit_level_actions_keyboard",
    "admin_deposit_levels_keyboard",
    "admin_deposit_management_keyboard",
    "admin_deposit_settings_keyboard",
    "admin_deposits_list_keyboard",
    "admin_financial_list_keyboard",
    "admin_finpass_request_actions_keyboard",
    "admin_finpass_request_list_keyboard",
    "admin_inquiry_detail_keyboard",
    "admin_inquiry_list_keyboard",
    "admin_inquiry_menu_keyboard",
    "admin_inquiry_response_keyboard",
    "admin_keyboard",
    "admin_management_keyboard",
    "admin_roi_applies_to_keyboard",
    "admin_roi_confirmation_keyboard",
    "admin_roi_corridor_menu_keyboard",
    "admin_roi_level_select_keyboard",
    "admin_roi_mode_select_keyboard",
    "admin_support_keyboard",
    "admin_support_ticket_keyboard",
    "admin_ticket_list_keyboard",
    "admin_user_financial_detail_keyboard",
    "admin_user_financial_keyboard",
    "admin_user_list_keyboard",
    "admin_user_profile_keyboard",
    "admin_users_keyboard",
    "admin_bonus_keyboard",
    "admin_cancel_keyboard",
    "admin_wallet_history_keyboard",
    "admin_wallet_keyboard",
    "admin_withdrawal_detail_keyboard",
    "admin_withdrawal_history_pagination_keyboard",
    "admin_withdrawal_settings_keyboard",
    "admin_withdrawals_keyboard",
    "admin_withdrawals_list_keyboard",
    "get_admin_keyboard_from_data",
    "withdrawal_confirm_keyboard",
    "withdrawal_list_keyboard",
]
