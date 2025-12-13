"""
AI Deposits Service - Core Module.

Contains base class initialization and shared utilities.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.deposit_repository import DepositRepository
from app.repositories.user_repository import UserRepository
from app.services.ai.commons import find_user_by_identifier, verify_admin


class AIDepositsServiceCore:
    """
    Base class for AI Deposits Service.

    Provides initialization and shared utility methods.
    ALL ADMINS are trusted to manage deposits via ARIA.
    """

    def __init__(
        self,
        session: AsyncSession,
        admin_data: dict[str, Any] | None = None,
    ):
        """
        Initialize AI Deposits Service.

        Args:
            session: Database session
            admin_data: Admin information (ID, username)
        """
        self.session = session
        self.admin_data = admin_data or {}
        self.admin_telegram_id = self.admin_data.get("ID")
        self.admin_username = self.admin_data.get("username")
        self.deposit_repo = DepositRepository(session)
        self.user_repo = UserRepository(session)

    async def _verify_admin(self) -> tuple[Any | None, str | None]:
        """
        Verify admin credentials using shared utility.

        Returns:
            Tuple of (admin_object, error_message)
        """
        return await verify_admin(
            self.session,
            self.admin_telegram_id,
        )

    def _is_trusted_admin(self) -> bool:
        """
        Check if current admin can modify deposits.

        Returns:
            True if admin is trusted (ALL admins are trusted)
        """
        return self.admin_telegram_id is not None

    async def _find_user(
        self,
        identifier: str,
    ) -> tuple[User | None, str | None]:
        """
        Find user by @username or telegram_id.

        Args:
            identifier: User @username or telegram_id

        Returns:
            Tuple of (user_object, error_message)
        """
        return await find_user_by_identifier(
            self.session,
            identifier,
            self.user_repo,
        )
