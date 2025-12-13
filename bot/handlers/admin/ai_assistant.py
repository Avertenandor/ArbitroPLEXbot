"""
AI Assistant Handler for Admins (Legacy).

This file is kept for backward compatibility.
The actual implementation has been moved to the ai_assistant package.

DEPRECATED: Import from bot.handlers.admin.ai_assistant instead.
"""

# Import router from new package structure for backward compatibility
from bot.handlers.admin.ai_assistant import router

__all__ = ["router"]
