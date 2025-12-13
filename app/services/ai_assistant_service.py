"""
AI Assistant Service.

DEPRECATED: This file is kept for backward compatibility only.
All functionality has been moved to app/services/ai_assistant/ module.

For new code, please use:
    from app.services.ai_assistant import (
        AIAssistantService,
        get_ai_service,
    )
"""

# Re-export everything from the new modular structure
from app.services.ai_assistant import (
    AIAssistantService,
    get_ai_service,
)

__all__ = [
    "AIAssistantService",
    "get_ai_service",
]
