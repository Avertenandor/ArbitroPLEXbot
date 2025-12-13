"""
AI System Administration Service - Core.

Main service class with initialization and authorization methods.
"""
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.ai.commons import verify_admin


class AISystemService:
    """
    AI-powered system administration service.

    SECURITY NOTES:
    - Access is granted to any verified (non-blocked) admin
    - All actions are logged

    NOTE: Access control
    Per requirement: any active (non-blocked) admin can operate
    AI system controls.
    The only gate is presence in DB `admins` and not blocked.
    """

    def __init__(
        self,
        session: AsyncSession,
        admin_data: dict[str, Any] | None = None,
    ):
        """
        Initialize AI System Service.

        Args:
            session: Database session
            admin_data: Admin user data from Telegram
        """
        self.session = session
        self.admin_data = admin_data or {}
        self.admin_telegram_id = self.admin_data.get("ID")
        self.admin_username = self.admin_data.get("username")

    async def _verify_admin(self) -> tuple[Any | None, str | None]:
        """
        Verify admin credentials.

        Returns:
            Tuple of (admin_object, error_message)
        """
        return await verify_admin(self.session, self.admin_telegram_id)

    def _is_super_admin(self) -> bool:
        """
        Check if admin has super-admin privileges.

        All verified admins have super-admin level access
        for ARYA controls.

        Returns:
            True for all verified admins
        """
        return True

    def _is_trusted_admin(self) -> bool:
        """
        Check if admin is trusted.

        All verified admins are trusted for ARYA controls.

        Returns:
            True for all verified admins
        """
        return True
