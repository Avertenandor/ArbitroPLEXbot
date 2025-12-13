"""
My Wallet module.

Provides comprehensive wallet information:
- Token balances (PLEX, USDT, BNB)
- Transaction history by token type
- Navigation between token transaction lists
"""

from aiogram import Router

from . import base_handlers, transaction_handlers

# Create combined router
router = Router()

# Include all sub-routers
router.include_router(base_handlers.router)
router.include_router(transaction_handlers.router)

__all__ = ["router"]
