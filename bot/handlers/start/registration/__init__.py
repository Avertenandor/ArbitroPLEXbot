"""
Registration flow module.

This module has been refactored into smaller, well-organized submodules:

- handlers.py: Main FSM handlers (cmd_start, process_wallet, etc.)
- validators.py: Validation utilities (wallet, password, phone, email)
- referral.py: Referral code parsing
- blacklist_checks.py: Blacklist verification functions
- helpers.py: Helper utilities (formatting, escaping, etc.)
- messages.py: Text constants and messages

All handlers and the router are re-exported here to maintain backward compatibility.
This allows other modules to import handlers directly from bot.handlers.start.registration
"""

# Re-export all public functions and router for backward compatibility
# Re-export blacklist checks
from .blacklist_checks import (
    check_registration_blacklist,
    check_wallet_blacklist,
    get_blacklist_entry,
)
from .handlers import (
    cmd_start,
    handle_contacts_choice,
    process_email,
    process_financial_password,
    process_password_confirmation,
    process_phone,
    process_wallet,
    router,
)

# Re-export helpers
from .helpers import (
    escape_markdown,
    format_balance,
    is_skip_command,
    normalize_button_text,
    reset_bot_blocked_flag,
)

# Re-export referral utilities
from .referral import parse_referral_code

# Re-export validators (might be useful for other modules)
from .validators import (
    normalize_phone,
    validate_email,
    validate_password,
    validate_phone,
)


__all__ = [
    # Main handlers (required for backward compatibility)
    "router",
    "cmd_start",
    "process_wallet",
    "process_financial_password",
    "process_password_confirmation",
    "handle_contacts_choice",
    "process_phone",
    "process_email",
    # Validators
    "validate_password",
    "validate_phone",
    "validate_email",
    "normalize_phone",
    # Referral
    "parse_referral_code",
    # Blacklist
    "check_registration_blacklist",
    "check_wallet_blacklist",
    "get_blacklist_entry",
    # Helpers
    "format_balance",
    "escape_markdown",
    "reset_bot_blocked_flag",
    "is_skip_command",
    "normalize_button_text",
]
