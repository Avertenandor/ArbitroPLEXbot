"""
Blacklist management module.

This module provides blacklist management functionality for administrators.
It has been refactored into smaller, organized sub-modules:

- menu.py: Main blacklist menu display
- add.py: Add users to blacklist
- remove.py: Remove users from blacklist
- view.py: View entry details and unban users
- notifications.py: Edit blacklist notification texts

All handlers are combined into a single router for easy registration.
"""

from aiogram import Router

# Import all sub-module routers
from bot.handlers.admin.blacklist.add import router as add_router
from bot.handlers.admin.blacklist.menu import (
    router as menu_router,
)
from bot.handlers.admin.blacklist.menu import (
    show_blacklist,  # Re-export for backward compatibility
)
from bot.handlers.admin.blacklist.notifications import (
    router as notifications_router,
)
from bot.handlers.admin.blacklist.remove import router as remove_router
from bot.handlers.admin.blacklist.view import router as view_router


# Create main router and include all sub-routers
router = Router()
router.include_router(menu_router)
router.include_router(add_router)
router.include_router(remove_router)
router.include_router(view_router)
router.include_router(notifications_router)

# Export main router and commonly used functions for backward compatibility
__all__ = ["router", "show_blacklist"]
