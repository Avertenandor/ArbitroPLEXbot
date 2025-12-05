"""
Admin Panel Module

This module provides comprehensive admin panel functionality split into logical submodules:

Submodules:
-----------
- auth: Master key authentication and session management
- main: Main admin panel entry points (/admin command, panel button)
- analytics: Analytics commands (retention, dashboard)
- statistics: Platform statistics (users, deposits, referrals, withdrawals)
- withdrawals: Withdrawal history with pagination
- navigation: Navigation handlers for various admin menus
- export: Data export functionality (CSV)

Structure:
----------
The original panel.py (893 lines) has been refactored into smaller, focused modules:
- auth.py (~240 lines) - Authentication flow
- main.py (~120 lines) - Main panel handlers
- analytics.py (~170 lines) - Analytics commands
- statistics.py (~170 lines) - Statistics display
- withdrawals.py (~130 lines) - Withdrawal history
- navigation.py (~130 lines) - Menu navigation
- export.py (~60 lines) - Data export

Usage:
------
Import the router from this package:
    from bot.handlers.admin.panel import router

Import specific functions (backward compatibility):
    from bot.handlers.admin.panel import handle_admin_panel_button

All functionality from the original panel.py is preserved and accessible.
"""

from aiogram import Router

# Import all submodule routers
from bot.handlers.admin.panel import (
    analytics,
    auth,
    export,
    main,
    navigation,
    statistics,
    withdrawals,
)

# Create main router and include all submodule routers
router = Router(name="admin_panel")

# Include all submodule routers
router.include_router(auth.router)
router.include_router(main.router)
router.include_router(analytics.router)
router.include_router(statistics.router)
router.include_router(withdrawals.router)
router.include_router(navigation.router)
router.include_router(export.router)

# Re-export commonly used functions for backward compatibility
from bot.handlers.admin.panel.auth import (  # noqa: E402
    get_admin_and_super_status,
    handle_master_key_input,
)
from bot.handlers.admin.panel.main import (  # noqa: E402
    cmd_admin_panel,
    handle_admin_panel_button,
    handle_back_to_main_menu,
)
from bot.handlers.admin.panel.navigation import (  # noqa: E402
    handle_admin_users_menu,
    handle_admin_withdrawals,
)
from bot.handlers.admin.panel.statistics import handle_admin_stats  # noqa: E402

# Export all public interfaces
__all__ = [
    "router",
    # Auth functions
    "get_admin_and_super_status",
    "handle_master_key_input",
    # Main functions
    "cmd_admin_panel",
    "handle_admin_panel_button",
    "handle_back_to_main_menu",
    # Navigation functions
    "handle_admin_users_menu",
    "handle_admin_withdrawals",
    # Statistics functions
    "handle_admin_stats",
]
