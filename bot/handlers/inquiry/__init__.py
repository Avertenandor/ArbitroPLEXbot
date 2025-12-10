"""
User Inquiry Handlers.

Handles user questions to admins via "Задать вопрос" button.

This module has been refactored into smaller, well-organized submodules:
- entry.py: Main entry point handler ("❓ Задать вопрос")
- question_input.py: Question input and validation
- dialog_basic.py: Basic dialog actions (history, cancel, close, back)
- dialog_media.py: Media handlers (photos, documents)
- dialog_messages.py: Text message handling in dialogs
- notifications.py: Admin notification helpers

All handlers are combined into a single router for backward compatibility.
"""

from aiogram import Router

# Import all routers from submodules
from . import (
    dialog_basic,
    dialog_media,
    dialog_messages,
    entry,
    notifications,
    question_input,
)


# Create main router and include all submodule routers
router = Router(name="user_inquiry")
router.include_router(entry.router)
router.include_router(question_input.router)
router.include_router(dialog_basic.router)
router.include_router(dialog_media.router)
router.include_router(dialog_messages.router)

# Re-export notification helper for backward compatibility
# (in case other modules import it directly)
__all__ = [
    "router",
    "notifications",
]
