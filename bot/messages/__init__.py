"""
Bot Messages Module
Contains all message templates and formatting functions for the bot
"""

# Import all from admin_messages
from bot.messages.admin_messages import (
    ADMIN_ACCESS_DENIED,
    ADMIN_NOT_FOUND,
    ADMIN_PANEL_WELCOME,
    BACK_TO_PANEL_BUTTON,
    CANCEL_BUTTON,
    OPERATION_CANCELLED,
    USER_BLOCKED_SUCCESS,
    USER_NOT_FOUND,
    USER_UNBLOCKED_SUCCESS,
    format_admin_list,
    format_user_profile,
)

# Import all from error_messages
from bot.messages.error_messages import (
    BLOCKCHAIN_ERROR,
    DATABASE_ERROR,
    ERROR_TYPES,
    GENERIC_ERROR,
    MAINTENANCE_MODE,
    NETWORK_ERROR,
    PERMISSION_DENIED,
    RATE_LIMIT_ERROR,
    SESSION_EXPIRED,
    TRY_AGAIN_LATER,
    VALIDATION_ERROR,
    detect_error_type,
    format_error_for_admin,
    format_error_for_user,
    get_user_error_message,
)

# Import all from user_messages
from bot.messages.user_messages import (
    AUTH_REQUIRED,
    BALANCE_INFO_TEMPLATE,
    DEPOSIT_INFO_TEMPLATE,
    INVALID_WALLET,
    MAIN_MENU_TEXT,
    PAYMENT_REQUIRED,
    PAYMENT_VERIFIED,
    REGISTRATION_COMPLETE,
    WALLET_PROMPT,
    WELCOME_MESSAGE,
    escape_markdown,
    format_balance,
    format_deposit_status,
    format_progress_bar,
    format_transaction_hash_short,
    format_usdt,
    format_wallet_short,
    format_withdrawal_status,
)

__all__ = [
    # Admin messages - constants
    "ADMIN_PANEL_WELCOME",
    "ADMIN_NOT_FOUND",
    "ADMIN_ACCESS_DENIED",
    "USER_NOT_FOUND",
    "USER_BLOCKED_SUCCESS",
    "USER_UNBLOCKED_SUCCESS",
    "OPERATION_CANCELLED",
    "BACK_TO_PANEL_BUTTON",
    "CANCEL_BUTTON",
    # Admin messages - functions
    "format_user_profile",
    "format_admin_list",
    # User messages - constants
    "WELCOME_MESSAGE",
    "AUTH_REQUIRED",
    "WALLET_PROMPT",
    "INVALID_WALLET",
    "PAYMENT_REQUIRED",
    "PAYMENT_VERIFIED",
    "REGISTRATION_COMPLETE",
    "MAIN_MENU_TEXT",
    "BALANCE_INFO_TEMPLATE",
    "DEPOSIT_INFO_TEMPLATE",
    # User messages - functions
    "format_balance",
    "format_deposit_status",
    "format_withdrawal_status",
    "format_usdt",
    "format_progress_bar",
    "format_wallet_short",
    "format_transaction_hash_short",
    "escape_markdown",
    # Error messages - constants
    "DATABASE_ERROR",
    "NETWORK_ERROR",
    "BLOCKCHAIN_ERROR",
    "VALIDATION_ERROR",
    "RATE_LIMIT_ERROR",
    "PERMISSION_DENIED",
    "SESSION_EXPIRED",
    "MAINTENANCE_MODE",
    "GENERIC_ERROR",
    "TRY_AGAIN_LATER",
    "ERROR_TYPES",
    # Error messages - functions
    "format_error_for_user",
    "format_error_for_admin",
    "detect_error_type",
    "get_user_error_message",
]
