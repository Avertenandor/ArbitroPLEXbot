"""
Admin Withdrawals Handlers Package.

This module has been refactored into smaller, focused modules:
- pending.py: Pending withdrawals list and pagination
- details.py: Withdrawal selection and detail view
- approval.py: Approval/rejection logic with dual control
- history.py: Approved and rejected withdrawals history
- navigation.py: Navigation handlers

The router is composed of all sub-routers to maintain backward compatibility.
Public functions are re-exported for external imports.
"""

from aiogram import Router

# Import all sub-routers
from bot.handlers.admin.withdrawals import (
    approval,
    details,
    history,
    navigation,
    pending,
)

# Import public functions for backward compatibility
from bot.handlers.admin.withdrawals.pending import handle_pending_withdrawals

# Create main router and include all sub-routers
router = Router(name="admin_withdrawals")

# Include all sub-routers in the correct order
# Pending handlers should be first for main entry point
router.include_router(pending.router)
# Details handlers for viewing individual withdrawals
router.include_router(details.router)
# Approval handlers for approve/reject operations
router.include_router(approval.router)
# History handlers for viewing approved/rejected lists
router.include_router(history.router)
# Navigation handlers should be last as they have broad filters
router.include_router(navigation.router)

# Export router and public functions for backward compatibility
__all__ = ["router", "handle_pending_withdrawals"]
