"""
Deposit handler.

Handles deposit creation flow with custom amount input in corridor.

This module has been refactored into a modular structure:
- deposit/level_selection.py - Handles level selection
- deposit/amount_input.py - Handles amount input and validation
- deposit/tx_hash.py - Handles transaction hash and deposit creation

Flow:
1. User selects level (test, level_1, ..., level_5) via button
2. System shows corridor (min-max amounts) for the level
3. User enters custom amount within corridor
4. System validates amount
5. System shows USDT payment details
6. User sends USDT and provides tx hash
7. Deposit is created

All handlers are imported from the deposit module.
"""

from aiogram import Router

# Import the main router from deposit module
from bot.handlers.deposit import router as deposit_router

# Re-export the router for compatibility
router = deposit_router

__all__ = ["router"]
