"""
Backward compatibility module for NotificationService.

This module re-exports NotificationService from the new package location.
All new code should import from app.services.notification instead.

Migration:
    Old: from app.services.notification_service import NotificationService
    New: from app.services.notification import NotificationService
"""

from app.services.notification import NotificationService

__all__ = ["NotificationService"]
