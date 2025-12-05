"""
Menu handlers package.

This package has been refactored from a single 1424-line file into smaller,
well-organized modules for better maintainability.

Module Organization:
--------------------
- core.py: Main menu display and navigation handlers
- balance.py: Balance display handlers
- deposit_menu.py: Deposit menu with level statuses
- withdrawal_menu.py: Withdrawal menu handlers
- referral_menu.py: Referral menu with stats
- settings.py: Settings menu handlers
- profile.py: User profile and report download
- wallet.py: Wallet information and history
- registration.py: Registration process from menu
- deposits.py: Active deposits listing
- notifications.py: Notification preferences
- language.py: Language selection
- info.py: Information pages (rules, ecosystem, partner)
- update.py: Deposit update/scan handlers

Backward Compatibility:
----------------------
This __init__.py maintains full backward compatibility by:
1. Importing and combining all routers into a single router
2. Re-exporting the show_main_menu function
3. Ensuring all imports from 'bot.handlers.menu' continue to work
"""

from aiogram import Router

# Import core function for backward compatibility
from bot.handlers.menu.core import show_main_menu

# Import all routers from submodules
from bot.handlers.menu import (
    balance,
    core,
    deposit_menu,
    deposits,
    info,
    language,
    notifications,
    profile,
    referral_menu,
    registration,
    settings,
    update,
    wallet,
    withdrawal_menu,
)

# Create combined router
router = Router()

# Include all sub-routers in the correct order
# Core menu handlers should be first
router.include_router(core.router)

# Balance and financial menus
router.include_router(balance.router)
router.include_router(deposit_menu.router)
router.include_router(withdrawal_menu.router)

# User profile and data
router.include_router(profile.router)
router.include_router(wallet.router)
router.include_router(deposits.router)

# Referral system
router.include_router(referral_menu.router)

# Settings and preferences
router.include_router(settings.router)
router.include_router(notifications.router)
router.include_router(language.router)

# Information pages
router.include_router(info.router)

# Actions
router.include_router(update.router)
router.include_router(registration.router)

# Export for backward compatibility
__all__ = [
    'router',
    'show_main_menu',
]
