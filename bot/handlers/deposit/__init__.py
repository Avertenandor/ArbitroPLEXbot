"""
Deposit handlers module.

This module contains all deposit-related handlers split into logical components:
- level_selection: Handles deposit level selection
- amount_input: Handles amount input and validation
- tx_hash: Handles transaction hash input and deposit creation

The main router combines all sub-routers.
"""

from aiogram import Router

from . import amount_input, level_selection, tx_hash

# Create main deposit router
router = Router()

# Include all sub-routers
router.include_router(level_selection.router)
router.include_router(amount_input.router)
router.include_router(tx_hash.router)

__all__ = ["router"]
