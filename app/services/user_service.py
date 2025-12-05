"""
Backward compatibility module for UserService.

This module re-exports UserService from the new package location.
All new code should import from app.services.user instead.

Migration:
    Old: from app.services.user_service import UserService
    New: from app.services.user import UserService
"""

from app.services.user import UserService

__all__ = ["UserService"]
