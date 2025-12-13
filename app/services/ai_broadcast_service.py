"""AI Broadcast Service - allows ARIA to send messages to users.

NOTE: This module has been refactored into a modular package.
Import from app.services.ai_broadcast for all functionality.
This file is kept for backward compatibility.
"""

# Backward compatibility: re-export from new modular structure
from app.services.ai_broadcast import AIBroadcastService

__all__ = ["AIBroadcastService"]
