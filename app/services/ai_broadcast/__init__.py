"""AI Broadcast Service - modular package."""

from app.services.ai_broadcast.core import AIBroadcastService
from app.services.ai_broadcast.sender import MessageSender
from app.services.ai_broadcast.targeting import UserTargeting

__all__ = [
    "AIBroadcastService",
    "MessageSender",
    "UserTargeting",
]
