"""
Admin handler for viewing user messages.

Allows admins to view text messages sent by users (with REPLY keyboards).

This module has been refactored into smaller, well-organized submodules:
- menu.py: Main menu entry point
- helpers.py: Helper functions (navigation, user search, formatting)
- search.py: User search and ID processing
- pagination.py: Pagination handlers and page display
- actions.py: Additional actions (statistics, delete, back to panel)

All handlers are combined into a single router for backward compatibility.
"""

from aiogram import Router

# Import all routers from submodules
from . import actions, helpers, menu, pagination, search

# Create main router and include all submodule routers
router = Router(name="admin_user_messages")
router.include_router(menu.router)
router.include_router(search.router)
router.include_router(pagination.router)
router.include_router(actions.router)

# Re-export helpers for backward compatibility
# (in case other modules import them directly)
__all__ = [
    "router",
    "helpers",
]
