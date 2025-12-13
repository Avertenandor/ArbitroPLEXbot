"""
Knowledge Base Management Package.

Modular handlers for managing ARIA's knowledge base.
All handlers are registered on a single router for easy integration.

Modules:
- router: Core router, states, and keyboard utilities
- menu: Main menu and statistics
- view: Viewing entries, categories, and navigation
- add: Adding new entries
- edit: Editing and verifying entries
- delete: Deleting entries
- search: Searching entries

Usage:
    from bot.handlers.admin.knowledge_base import router

    # Register with dispatcher
    dp.include_router(router)
"""

# Import all modules to register their handlers
from . import add, delete, edit, menu, search, view

# Re-export router for backward compatibility
from .router import router

__all__ = ["router", "add", "delete", "edit", "menu", "search", "view"]
