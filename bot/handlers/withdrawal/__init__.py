"""
Withdrawal handlers package.

This package has been refactored from a single large file (749 lines) into smaller,
well-organized modules for better maintainability:

- eligibility.py: User eligibility and verification checks
- auto_payout.py: Automatic withdrawal processing
- handlers.py: Main withdrawal menu and entry point handlers
- processors.py: Amount validation and financial password processing
- history.py: Withdrawal history display with pagination

All public interfaces are re-exported here to maintain backward compatibility.
"""

from aiogram import Router

# Import routers from each module
from . import handlers, history, processors

# Import all public functions for backward compatibility
from .auto_payout import (
    _safe_process_auto_payout,
    process_auto_payout,
)
from .eligibility import (
    check_withdrawal_eligibility,
    is_level1_only_user,
)
from .history import (
    _show_withdrawal_history,
    show_history,
)


# Create main router and include all sub-routers
router = Router()
router.include_router(handlers.router)
router.include_router(processors.router)
router.include_router(history.router)

# Export all public interfaces
__all__ = [
    # Main router (used by bot/main.py)
    "router",
    # Eligibility functions
    "is_level1_only_user",
    "check_withdrawal_eligibility",
    # Auto-payout functions
    "_safe_process_auto_payout",
    "process_auto_payout",
    # History functions
    "show_history",
    "_show_withdrawal_history",
]
