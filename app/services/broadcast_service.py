"""
Broadcast Service (Compatibility Layer).

This module provides backward compatibility by re-exporting
BroadcastService from the broadcast package.

For new code, prefer importing directly from:
    from app.services.broadcast import BroadcastService
"""

# Re-export for backward compatibility
from app.services.broadcast import BroadcastService

__all__ = ["BroadcastService"]
