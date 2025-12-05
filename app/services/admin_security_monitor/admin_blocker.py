"""
Admin Security Monitor - Admin Blocker Module.

Module: admin_blocker.py
Handles admin blocking, notifications, and session management.
R10-3: Automatically blocks compromised admins.
"""

from loguru import logger


class AdminBlocker:
    """Admin blocking and notification logic."""

    def __init__(self, admin_repo, session, bot=None, redis_client=None) -> None:
        """Initialize admin blocker."""
        self.admin_repo = admin_repo
        self.session = session
        self.bot = bot
        self.redis_client = redis_client

    async def block_admin(
        self, admin_id: int, reason: str
    ) -> tuple[bool, str | None]:
        """
        Block compromised admin.

        R10-3: Automatically blocks admin when compromise detected.

        Args:
            admin_id: Admin to block
            reason: Block reason

        Returns:
            Tuple of (success, error_message)
        """
        try:
            admin = await self.admin_repo.get_by_id(admin_id)
            if not admin:
                return False, "Admin not found"

            # R10-3: Mark admin as blocked
            logger.critical(
                f"R10-3: Admin {admin_id} being blocked: {reason}",
                extra={
                    "admin_id": admin_id,
                    "admin_telegram_id": admin.telegram_id,
                    "reason": reason,
                },
            )

            # Update is_blocked field
            await self.admin_repo.update(admin_id, is_blocked=True)

            # Invalidate all sessions for this admin
            await self._force_logout(admin_id)

            # Block critical operations
            await self._block_critical_operations(admin_id)

            # Notify super_admins
            await self._notify_super_admins(
                admin_id, reason, severity="critical"
            )

            await self.session.commit()

            return True, None

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to block admin {admin_id}: {e}")
            return False, str(e)

    async def _notify_super_admins(
        self, admin_id: int, reason: str, severity: str = "high"
    ) -> None:
        """
        Notify super_admins about suspicious admin activity.

        R10-3: Sends Telegram notifications to all super_admins.

        Args:
            admin_id: Admin ID with suspicious activity
            reason: Reason for notification
            severity: Severity level ("critical" | "high" | "medium")
        """
        if not self.bot:
            logger.warning(
                "Bot instance not provided, cannot send super_admin notifications"
            )
            return

        try:
            from app.services.notification_service import NotificationService

            # Get admin details
            admin = await self.admin_repo.get_by_id(admin_id)
            if not admin:
                return

            # Get all super_admins
            all_admins = await self.admin_repo.find_by()
            super_admins = [a for a in all_admins if a.is_super_admin]

            if not super_admins:
                logger.warning("No super_admins found to notify")
                return

            # Build notification message
            emoji = "🚨" if severity == "critical" else "⚠️"
            message = (
                f"{emoji} **SECURITY ALERT: Suspicious Admin Activity**\n\n"
                f"**Admin:** {admin.display_name or admin.telegram_id}\n"
                f"**Admin ID:** {admin_id}\n"
                f"**Severity:** {severity.upper()}\n"
                f"**Reason:** {reason}\n\n"
                f"Action required: Review admin activity immediately."
            )

            # Send notifications
            notification_service = NotificationService(self.session)
            for super_admin in super_admins:
                try:
                    await notification_service.send_notification(
                        bot=self.bot,
                        user_telegram_id=super_admin.telegram_id,
                        message=message,
                        critical=(severity == "critical"),
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to notify super_admin {super_admin.id}: {e}"
                    )

        except Exception as e:
            logger.error(f"Error notifying super_admins: {e}", exc_info=True)

    async def _force_logout(self, admin_id: int) -> None:
        """
        Force logout admin by invalidating all sessions.

        R10-3: Deactivates all active admin sessions.

        Args:
            admin_id: Admin ID to logout
        """
        try:
            from app.repositories.admin_session_repository import (
                AdminSessionRepository,
            )

            session_repo = AdminSessionRepository(self.session)
            deactivated_count = await session_repo.deactivate_all_sessions(admin_id)
            await self.session.commit()

            logger.warning(
                f"R10-3: Forced logout for admin {admin_id}: "
                f"{deactivated_count} sessions deactivated"
            )

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error forcing logout for admin {admin_id}: {e}")

    async def _block_critical_operations(self, admin_id: int) -> None:
        """
        Temporarily block critical operations for compromised admin.

        R10-3: Sets Redis flag to block critical operations.
        R11-2: Gracefully handles Redis failures.

        Args:
            admin_id: Admin ID to block
        """
        if not self.redis_client:
            logger.warning(
                "R11-2: Redis client not provided, cannot set operation block. "
                "Admin will be blocked via database flag only."
            )
            return

        try:
            # Block for 1 hour (3600 seconds)
            block_key = f"admin:{admin_id}:operations_blocked"
            await self.redis_client.set(block_key, "1", ex=3600)

            logger.warning(
                f"R10-3: Critical operations blocked for admin {admin_id} "
                f"for 1 hour"
            )
        except Exception as e:
            # R11-2: Redis failed, but admin is already blocked in database
            logger.warning(
                f"R11-2: Failed to set Redis block for admin {admin_id}: {e}. "
                "Admin is still blocked via database flag."
            )
            logger.error(
                f"Error blocking operations for admin {admin_id}: {e}"
            )
