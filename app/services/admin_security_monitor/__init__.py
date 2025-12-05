"""
Admin Security Monitor - Main Module.

This module monitors admin actions for suspicious patterns and automatically
blocks compromised admins.

Module Structure:
- core.py: Main service class and check_action orchestration
- action_checks.py: Specific action checking logic
- admin_blocker.py: Admin blocking and notifications

Public Interface:
- AdminSecurityMonitor: Main service class (backward compatible)

Detects:
- Mass bans/terminations (>20/hour)
- Mass withdrawal approvals (>50/hour)
- Admin creation/deletion spikes (>5/day)
- Unusual timing (3am operations)
- Large withdrawal approvals (>$1000)
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from .admin_blocker import AdminBlocker
from .core import AdminSecurityCore


class AdminSecurityMonitor:
    """
    R10-3: Monitor admin actions for compromise detection.

    Automatically blocks admins when suspicious patterns are detected.
    Thresholds are configurable via settings.py / .env

    This is the main service class that provides backward compatibility
    with the original monolithic implementation.
    """

    def __init__(
        self,
        session: AsyncSession,
        bot: Any | None = None,
        redis_client: Any | None = None,
    ) -> None:
        """
        Initialize admin security monitor.

        Args:
            session: Database session
            bot: Optional Bot instance for notifications
            redis_client: Optional Redis client for temporary blocks
        """
        self.session = session
        self.bot = bot
        self.redis_client = redis_client

        # Initialize all components
        self.core = AdminSecurityCore(session, bot, redis_client)
        self.admin_blocker = AdminBlocker(
            self.core.admin_repo,
            session,
            bot,
            redis_client
        )

        # Expose repositories for backward compatibility
        self.action_repo = self.core.action_repo
        self.admin_repo = self.core.admin_repo

    # Delegate methods to appropriate components for backward compatibility

    async def check_action(
        self,
        admin_id: int,
        action_type: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Check if admin action is suspicious."""
        return await self.core.check_action(admin_id, action_type, details)

    async def block_admin(
        self, admin_id: int, reason: str
    ) -> tuple[bool, str | None]:
        """Block compromised admin."""
        return await self.admin_blocker.block_admin(admin_id, reason)


# Re-export for backward compatibility
__all__ = ['AdminSecurityMonitor']
