"""
AI Assistant handler package.

This package contains AI assistant handlers split into logical modules:
- utils.py: Helper functions, states, and keyboards
- menu.py: Menu navigation handlers
- conversation.py: AI chat conversation handlers
- actions.py: ARIA admin action handlers
- router.py: Main router combining all sub-routers

For backward compatibility, the main router is re-exported here.
"""

from .router import router

__all__ = ["router"]
