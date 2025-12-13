"""PLEX Payment Service - Legacy compatibility module.

This module provides backward compatibility for existing imports.
The actual implementation has been moved to app.services.plex_payment.

DEPRECATED: Import from app.services.plex_payment instead.
"""

from app.services.plex_payment import PlexPaymentService

__all__ = ["PlexPaymentService"]
