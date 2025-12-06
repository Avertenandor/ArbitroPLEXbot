"""
Contact Update Handler - ТОЛЬКО REPLY KEYBOARDS!

Handles user contact information updates (phone and email).

This module has been refactored into separate submodules:
- menu.py: Contact type selection and menu navigation
- phone.py: Phone number update handlers
- email.py: Email address update handlers
- utils.py: Helper functions

The main router combines all submodule routers for backward compatibility.
"""

from aiogram import Router

from . import email, menu, phone

# Create main router that includes all submodule routers
router = Router(name="contact_update")

# Include all submodule routers in the correct order
router.include_router(menu.router)
router.include_router(phone.router)
router.include_router(email.router)

# Re-export utility functions for backward compatibility
from .utils import get_user_or_error, navigate_to_home

__all__ = [
    "router",
    "get_user_or_error",
    "navigate_to_home",
]
