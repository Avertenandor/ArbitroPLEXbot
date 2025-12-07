"""
Admin keyboards package.

This package contains modular admin keyboard components organized by functionality:

- main_keyboards: Primary admin panel keyboard
- user_keyboards: User management keyboards
- withdrawal_keyboards: Withdrawal management keyboards
- wallet_keyboards: Wallet management keyboards
- broadcast_keyboards: Message broadcast keyboards
- support_keyboards: Support ticket keyboards
- blacklist_keyboards: Blacklist management keyboards
- admin_management_keyboards: Admin management keyboards (super admin only)
- deposit_keyboards: Deposit and ROI management keyboards
- financial_keyboards: Financial reporting keyboards
- inquiry_keyboards: User inquiry management keyboards
- blockchain_keyboards: Blockchain provider settings keyboards
- emergency_keyboards: Emergency stop control keyboards

All keyboard functions are re-exported here for convenient access.
"""

# Main admin keyboards
from bot.keyboards.admin.main_keyboards import (
    admin_keyboard,
    get_admin_keyboard_from_data,
)

# User management keyboards
from bot.keyboards.admin.user_keyboards import (
    admin_bonus_keyboard,
    admin_cancel_keyboard,
    admin_user_list_keyboard,
    admin_user_profile_keyboard,
    admin_users_keyboard,
)

# Withdrawal management keyboards
from bot.keyboards.admin.withdrawal_keyboards import (
    admin_withdrawal_detail_keyboard,
    admin_withdrawal_history_pagination_keyboard,
    admin_withdrawal_settings_keyboard,
    admin_withdrawals_keyboard,
    withdrawal_confirm_keyboard,
    withdrawal_list_keyboard,
)

# Wallet management keyboards
from bot.keyboards.admin.wallet_keyboards import (
    admin_wallet_keyboard,
)

# Broadcast keyboards
from bot.keyboards.admin.broadcast_keyboards import (
    admin_broadcast_button_choice_keyboard,
    admin_broadcast_cancel_keyboard,
    admin_broadcast_keyboard,
)

# Support ticket keyboards
from bot.keyboards.admin.support_keyboards import (
    admin_support_keyboard,
    admin_support_ticket_keyboard,
    admin_ticket_list_keyboard,
)

# Blacklist management keyboards
from bot.keyboards.admin.blacklist_keyboards import (
    admin_blacklist_keyboard,
)

# Admin management keyboards
from bot.keyboards.admin.admin_management_keyboards import (
    admin_management_keyboard,
)

# Deposit management keyboards
from bot.keyboards.admin.deposit_keyboards import (
    admin_deposit_level_actions_keyboard,
    admin_deposit_levels_keyboard,
    admin_deposit_management_keyboard,
    admin_deposit_settings_keyboard,
    admin_roi_applies_to_keyboard,
    admin_roi_confirmation_keyboard,
    admin_roi_corridor_menu_keyboard,
    admin_roi_level_select_keyboard,
    admin_roi_mode_select_keyboard,
)

# Financial reporting keyboards
from bot.keyboards.admin.financial_keyboards import (
    admin_back_keyboard,
    admin_deposits_list_keyboard,
    admin_financial_list_keyboard,
    admin_finpass_request_actions_keyboard,
    admin_finpass_request_list_keyboard,
    admin_user_financial_detail_keyboard,
    admin_user_financial_keyboard,
    admin_wallet_history_keyboard,
    admin_withdrawals_list_keyboard,
)

# User inquiry keyboards
from bot.keyboards.admin.inquiry_keyboards import (
    admin_inquiry_detail_keyboard,
    admin_inquiry_list_keyboard,
    admin_inquiry_menu_keyboard,
    admin_inquiry_response_keyboard,
)

# Blockchain settings keyboards
from bot.keyboards.admin.blockchain_keyboards import (
    blockchain_settings_keyboard,
)

# Emergency stop keyboards
from bot.keyboards.admin.emergency_keyboards import (
    emergency_stops_keyboard,
)

# Export all functions
__all__ = [
    # Main keyboards
    "admin_keyboard",
    "get_admin_keyboard_from_data",
    # User management
    "admin_users_keyboard",
    "admin_user_list_keyboard",
    "admin_user_profile_keyboard",
    "admin_bonus_keyboard",
    "admin_cancel_keyboard",
    # Withdrawal management
    "admin_withdrawals_keyboard",
    "withdrawal_list_keyboard",
    "admin_withdrawal_detail_keyboard",
    "withdrawal_confirm_keyboard",
    "admin_withdrawal_settings_keyboard",
    "admin_withdrawal_history_pagination_keyboard",
    # Wallet management
    "admin_wallet_keyboard",
    # Broadcast
    "admin_broadcast_button_choice_keyboard",
    "admin_broadcast_cancel_keyboard",
    "admin_broadcast_keyboard",
    # Support tickets
    "admin_support_keyboard",
    "admin_support_ticket_keyboard",
    "admin_ticket_list_keyboard",
    # Blacklist
    "admin_blacklist_keyboard",
    # Admin management
    "admin_management_keyboard",
    # Deposit management
    "admin_deposit_settings_keyboard",
    "admin_deposit_management_keyboard",
    "admin_deposit_levels_keyboard",
    "admin_deposit_level_actions_keyboard",
    "admin_roi_corridor_menu_keyboard",
    "admin_roi_level_select_keyboard",
    "admin_roi_mode_select_keyboard",
    "admin_roi_applies_to_keyboard",
    "admin_roi_confirmation_keyboard",
    # Financial reporting
    "admin_finpass_request_list_keyboard",
    "admin_finpass_request_actions_keyboard",
    "admin_financial_list_keyboard",
    "admin_user_financial_keyboard",
    "admin_back_keyboard",
    "admin_user_financial_detail_keyboard",
    "admin_deposits_list_keyboard",
    "admin_withdrawals_list_keyboard",
    "admin_wallet_history_keyboard",
    # User inquiries
    "admin_inquiry_menu_keyboard",
    "admin_inquiry_list_keyboard",
    "admin_inquiry_detail_keyboard",
    "admin_inquiry_response_keyboard",
    # Blockchain settings
    "blockchain_settings_keyboard",
    # Emergency stops
    "emergency_stops_keyboard",
]
