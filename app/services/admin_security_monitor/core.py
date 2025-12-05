"""
Admin Security Monitor - Core Module.

Module: core.py
Main service class and action checking orchestration.
R10-3: Monitors admin actions for suspicious patterns and automatically blocks compromised admins.
"""

from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.admin_action_repository import AdminActionRepository
from app.repositories.admin_repository import AdminRepository


class AdminSecurityCore:
    """Core admin security monitoring."""

    def __init__(
        self,
        session: AsyncSession,
        bot: Any | None = None,
        redis_client: Any | None = None,
    ) -> None:
        """
        Initialize admin security core.

        Args:
            session: Database session
            bot: Optional Bot instance for notifications
            redis_client: Optional Redis client for temporary blocks
        """
        self.session = session
        self.bot = bot
        self.redis_client = redis_client
        self.action_repo = AdminActionRepository(session)
        self.admin_repo = AdminRepository(session)

    async def check_action(
        self,
        admin_id: int,
        action_type: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Check if admin action is suspicious.

        R10-3: Called after each admin action to detect compromise.

        Args:
            admin_id: Admin who performed action
            action_type: Type of action
            details: Action details (for withdrawal amounts, etc.)

        Returns:
            Dict with:
                - suspicious: bool
                - reason: str | None
                - should_block: bool
                - severity: "critical" | "high" | "medium"
        """
        try:
            # Get admin
            admin = await self.admin_repo.get_by_id(admin_id)
            if not admin:
                return {
                    "suspicious": False,
                    "reason": None,
                    "should_block": False,
                    "severity": None,
                }

            # Import action checker to avoid circular dependency
            from .action_checks import ActionChecker
            checker = ActionChecker(self.action_repo, self.session)

            # Check different action types
            if action_type in ("USER_BLOCKED", "USER_TERMINATED"):
                return await checker.check_mass_user_actions(
                    admin_id, action_type
                )
            elif action_type == "WITHDRAWAL_APPROVED":
                return await checker.check_withdrawal_approval(
                    admin_id, details
                )
            elif action_type == "BALANCE_ADJUSTMENT":
                # R18-4: Check balance adjustment limits
                return await checker.check_balance_adjustment_limits(admin_id)
            elif action_type in ("ADMIN_CREATED", "ADMIN_DELETED"):
                return await checker.check_admin_management(admin_id, action_type)
            elif action_type in (
                "SETTINGS_CHANGED",
                "WALLET_CHANGED",
                "SYSTEM_CONFIG_CHANGED",
            ):
                return await checker.check_critical_config_changes(
                    admin_id, action_type
                )

            # No suspicious pattern detected
            return {
                "suspicious": False,
                "reason": None,
                "should_block": False,
                "severity": None,
            }

        except Exception as e:
            logger.error(
                f"Error checking admin action: {e}",
                extra={"admin_id": admin_id, "action_type": action_type},
            )
            # On error, don't block (fail open)
            return {
                "suspicious": False,
                "reason": None,
                "should_block": False,
                "severity": None,
            }
