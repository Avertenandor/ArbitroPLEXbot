"""
Financial reporting module.

This module provides financial reporting functionality for administrators.
It has been refactored into smaller, organized sub-modules:

- states.py: FSM states definition
- formatters.py: Helper functions for formatting financial data
- list.py: User list with financial summary and pagination
- user_detail.py: Detailed user financial card
- deposits.py: Full deposits list with pagination
- withdrawals.py: Full withdrawals list with pagination
- wallet_history.py: Wallet change history
- navigation.py: Back navigation and return to admin panel

All handlers are combined into a single router for easy registration.
"""

from aiogram import Router

# Import states for external use
from bot.handlers.admin.financials.states import AdminFinancialStates

# Import all sub-module routers
from bot.handlers.admin.financials.deposits import router as deposits_router
from bot.handlers.admin.financials.list import (
    router as list_router,
    show_financial_list,  # Re-export for backward compatibility
)
from bot.handlers.admin.financials.navigation import router as navigation_router
from bot.handlers.admin.financials.user_detail import router as user_detail_router
from bot.handlers.admin.financials.wallet_history import (
    router as wallet_history_router,
)
from bot.handlers.admin.financials.withdrawals import router as withdrawals_router

# Create main router and include all sub-routers
router = Router()
router.include_router(list_router)
router.include_router(user_detail_router)
router.include_router(deposits_router)
router.include_router(withdrawals_router)
router.include_router(wallet_history_router)
router.include_router(navigation_router)

# Export main router, states, and commonly used functions for backward compatibility
__all__ = ["router", "AdminFinancialStates", "show_financial_list"]
