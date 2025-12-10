"""
Admin Management Module.

This module handles all admin-related operations including:
- Admin creation with role assignment
- Listing all administrators
- Admin deletion
- Emergency admin blocking

Module Structure:
- router.py: Main router for all admin handlers
- menu.py: Admin management menu
- create.py: Admin creation handlers
- list.py: Admin listing handlers
- delete.py: Admin deletion handlers
- emergency.py: Emergency blocking handlers

Usage:
    from bot.handlers.admin.admins import router
    from bot.handlers.admin.admins import show_admin_management

All handlers are automatically registered on the router.
"""

# Import router first
# Import all handlers to register them on the router
from . import create, delete, emergency, list, menu
from .create import handle_admin_role_selection, handle_admin_telegram_id, handle_create_admin
from .delete import handle_delete_admin, handle_delete_admin_telegram_id
from .emergency import handle_emergency_block_admin, handle_emergency_block_admin_telegram_id
from .list import handle_list_admins

# Re-export main functions for backward compatibility
from .menu import show_admin_management
from .router import router


# Public API
__all__ = [
    "router",
    "show_admin_management",
    "handle_create_admin",
    "handle_admin_telegram_id",
    "handle_admin_role_selection",
    "handle_list_admins",
    "handle_delete_admin",
    "handle_delete_admin_telegram_id",
    "handle_emergency_block_admin",
    "handle_emergency_block_admin_telegram_id", "menu", "create", "list", "delete", "emergency",
]
