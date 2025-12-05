"""
Admin Inquiry Handlers Package.

This module has been refactored into smaller, focused modules:
- menu.py: Main entry point for inquiry management
- lists.py: Handlers for different inquiry lists (new, my, closed)
- details.py: Inquiry detail viewing
- actions.py: Take and close inquiry actions
- responses.py: Admin response handlers (text, photo, document)
- navigation.py: Navigation handlers

The router is composed of all sub-routers to maintain backward compatibility.
"""

from aiogram import Router

# Import all sub-routers
from bot.handlers.admin.inquiries import (
    actions,
    details,
    lists,
    menu,
    navigation,
    responses,
)

# Create main router and include all sub-routers
router = Router(name="admin_inquiry")

# Include all sub-routers in the correct order
# Menu handlers should be first for main entry point
router.include_router(menu.router)
# Lists handlers for viewing different inquiry lists
router.include_router(lists.router)
# Details handlers for viewing individual inquiries
router.include_router(details.router)
# Actions handlers for take/close operations
router.include_router(actions.router)
# Responses handlers for replying to users
router.include_router(responses.router)
# Navigation handlers should be last as they have broad filters
router.include_router(navigation.router)

# Export router for backward compatibility
__all__ = ["router"]
