"""
Start handler module.

This module has been refactored into smaller, well-organized submodules:

- registration.py: Registration flow handlers (/start, wallet input, password setup, contacts)
- authentication.py: Auth and payment handlers (wallet verification, payment checking)
- callbacks.py: Callback query handlers (show password, rescan deposits, start after auth)
- reply_handlers.py: Reply keyboard handlers (payment confirmation, retry, show password)

All handlers are re-exported here to maintain backward compatibility.
"""

from aiogram import Router

# Import all routers from submodules
from . import authentication, callbacks, registration, reply_handlers

# Create a main router that includes all submodule routers
router = Router()

# Include all submodule routers in the correct order
# Registration handlers should be first (includes /start command)
router.include_router(registration.router)
# Authentication handlers
router.include_router(authentication.router)
# Callback handlers
router.include_router(callbacks.router)
# Reply keyboard handlers
router.include_router(reply_handlers.router)

# Re-export all handler functions for backward compatibility
# This allows other modules to import handlers directly from bot.handlers.start

# Registration handlers
from .registration import (
    cmd_start,
    handle_contacts_choice,
    process_email,
    process_financial_password,
    process_password_confirmation,
    process_phone,
    process_wallet,
)

# Authentication handlers
from .authentication import (
    ECOSYSTEM_INFO,
    handle_check_payment,
    handle_wallet_input,
    process_payment_wallet,
)

# Callback handlers
from .callbacks import (
    handle_rescan_deposits,
    handle_show_password_again,
    handle_start_after_auth,
)

# Reply keyboard handlers
from .reply_handlers import (
    handle_continue_without_deposit_reply,
    handle_payment_confirmed_reply,
    handle_rescan_deposits_reply,
    handle_retry_payment_reply,
    handle_show_password_reply,
    handle_start_work_reply,
)

# Export all public symbols
__all__ = [
    "router",
    # Registration handlers
    "cmd_start",
    "process_wallet",
    "process_financial_password",
    "process_password_confirmation",
    "handle_contacts_choice",
    "process_phone",
    "process_email",
    # Authentication handlers
    "ECOSYSTEM_INFO",
    "handle_check_payment",
    "process_payment_wallet",
    "handle_wallet_input",
    # Callback handlers
    "handle_show_password_again",
    "handle_rescan_deposits",
    "handle_start_after_auth",
    # Reply keyboard handlers
    "handle_payment_confirmed_reply",
    "handle_start_work_reply",
    "handle_rescan_deposits_reply",
    "handle_continue_without_deposit_reply",
    "handle_retry_payment_reply",
    "handle_show_password_reply",
]
