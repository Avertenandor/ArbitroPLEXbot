"""
Admin Deposit Management Module

This module provides comprehensive deposit management functionality split into logical submodules:

Submodules:
-----------
- menu: Main deposit management menu and general statistics
- search: User deposit search functionality
- levels: Level management display and configuration
- actions: Level enable/disable actions and max level management
- reports: Pending deposits and ROI statistics
- navigation: Back navigation to admin panel

Structure:
----------
The original deposit_management.py (886 lines) has been refactored into smaller, focused modules:
- menu.py (~150 lines) - Main menu and statistics
- search.py (~180 lines) - User deposit search
- levels.py (~170 lines) - Level management display
- actions.py (~300 lines) - Level actions and confirmations
- reports.py (~160 lines) - Pending deposits and ROI stats
- navigation.py (~40 lines) - Navigation handlers

Usage:
------
Import the router from this package:
    from bot.handlers.admin.deposit_management import router

Import specific functions (backward compatibility):
    from bot.handlers.admin.deposit_management import show_deposit_management_menu

All functionality from the original deposit_management.py is preserved and accessible.
"""

from aiogram import Router

# Import all submodule routers
from bot.handlers.admin.deposit_management import (
    actions,
    levels,
    menu,
    navigation,
    reports,
    search,
)

# Create main router and include all submodule routers
router = Router(name="admin_deposit_management")

# Include all submodule routers
router.include_router(menu.router)
router.include_router(search.router)
router.include_router(levels.router)
router.include_router(actions.router)
router.include_router(reports.router)
router.include_router(navigation.router)

# Re-export commonly used functions for backward compatibility
from bot.handlers.admin.deposit_management.menu import (  # noqa: E402
    show_deposit_management_menu,
    show_deposit_statistics,
)
from bot.handlers.admin.deposit_management.levels import (  # noqa: E402
    show_levels_management,
    show_level_actions_for_level,
)

# Export all public interfaces
__all__ = [
    "router",
    # Menu functions
    "show_deposit_management_menu",
    "show_deposit_statistics",
    # Levels functions
    "show_levels_management",
    "show_level_actions_for_level",
]
