"""
AI Assistant main router.

Combines all AI assistant sub-routers into one main router.
"""

from aiogram import Router

from . import action_flows, actions, conversation, menu


# Create main router
router = Router(name="admin_ai_assistant")

# Include all sub-routers in correct order
# Actions should be first (more specific handlers)
router.include_router(actions.router)
# Action flows (multi-step interactions)
router.include_router(action_flows.router)
# Menu handlers
router.include_router(menu.router)
# Conversation handlers (most general, should be last)
router.include_router(conversation.router)


__all__ = ["router"]
