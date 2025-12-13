"""
AI Users Service.

Provides comprehensive user management tools for AI assistant.
Includes: search, profile, balance changes, blocking, deposits.

SECURITY:
- Only accessible from authenticated admin session
- All admin roles can perform user operations (balance changes, etc.)
- All operations are logged for audit purposes
"""
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository

from .deposits import DepositsMixin
from .operations import OperationsMixin
from .profile import ProfileMixin


class AIUsersService(ProfileMixin, OperationsMixin, DepositsMixin):
    """
    AI-powered user management service.

    Provides full user management capabilities for ARIA.
    Uses mixin pattern for modular organization.
    """

    def __init__(
        self,
        session: AsyncSession,
        admin_data: dict[str, Any] | None = None,
    ):
        self.session = session
        self.admin_data = admin_data or {}
        self.admin_telegram_id = self.admin_data.get("ID")
        self.admin_username = self.admin_data.get("username")
        self.user_repo = UserRepository(session)


__all__ = ['AIUsersService']
