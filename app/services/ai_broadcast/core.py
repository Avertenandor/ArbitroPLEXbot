"""AI Broadcast Service - main service class."""

from typing import Any

from aiogram import Bot
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.commons import verify_admin
from app.services.ai_broadcast.sender import MessageSender
from app.services.ai_broadcast.targeting import UserTargeting


class AIBroadcastService:
    """Service for ARIA to send messages and broadcasts."""

    def __init__(
        self,
        session: AsyncSession,
        bot: Bot,
        admin_telegram_id: int | None = None,
        admin_username: str | None = None,
    ):
        self.session = session
        self.bot = bot
        self.admin_telegram_id = admin_telegram_id
        self.admin_username = admin_username

        # Initialize components
        self.targeting = UserTargeting(session)
        self.sender = MessageSender(session, bot, self.targeting)

    async def _verify_admin(self) -> tuple[bool, str | None]:
        """Verify that the caller is an active (non-blocked) admin."""
        admin, error = await verify_admin(
            self.session, self.admin_telegram_id
        )
        if error:
            return False, error
        return True, None

    async def send_message_to_user(
        self,
        user_identifier: str | int,
        message_text: str,
        parse_mode: str = "Markdown",
    ) -> dict[str, Any]:
        """
        Send a single message to a user.

        Args:
            user_identifier: @username, telegram_id, or ID:xxx
            message_text: Message text to send
            parse_mode: Markdown or HTML

        Returns:
            Result dict with status
        """
        ok, err = await self._verify_admin()
        if not ok:
            logger.warning(
                f"BROADCAST DENIED: {err} "
                f"(admin_id={self.admin_telegram_id})"
            )
            return {"success": False, "error": err}

        return await self.sender.send_to_user(
            user_identifier,
            message_text,
            self.admin_telegram_id,
            parse_mode,
        )

    async def broadcast_to_group(
        self,
        group: str,
        message_text: str,
        limit: int = 100,
        parse_mode: str = "Markdown",
    ) -> dict[str, Any]:
        """
        Broadcast message to a group of users.

        Args:
            group: Group type:
                - "active_appeals" - users with open appeals
                - "active_deposits" - users with active deposits
                - "active_24h" - users active in last 24 hours
                - "all" - all users (careful!)
            message_text: Message to send
            limit: Max users to send to
            parse_mode: Markdown or HTML

        Returns:
            Result dict with stats
        """
        ok, err = await self._verify_admin()
        if not ok:
            logger.warning(
                f"BROADCAST DENIED: {err} "
                f"(admin_id={self.admin_telegram_id}) "
                f"attempted broadcast to group '{group}'"
            )
            return {"success": False, "error": err}

        return await self.sender.broadcast_to_group(
            group, message_text, limit, parse_mode
        )

    async def get_users_list(
        self,
        group: str = "all",
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Get list of users for preview before broadcast.

        Args:
            group: Group type (same as broadcast_to_group)
            limit: Max users to return

        Returns:
            List of users with details
        """
        try:
            users = (
                await self.targeting.get_users_details_by_group(
                    group, limit
                )
            )

            return {
                "success": True,
                "group": group,
                "total": len(users),
                "users": users,
            }

        except Exception as e:
            logger.error(f"Get users list error: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def invite_to_dialog(
        self,
        user_identifier: str | int,
        custom_message: str | None = None,
    ) -> dict[str, Any]:
        """
        Send personal invitation to dialog with ARIA.

        Args:
            user_identifier: @username, telegram_id, or ID:xxx
            custom_message: Optional custom message

        Returns:
            Result dict
        """
        return await self.sender.send_invitation(
            user_identifier, custom_message
        )

    async def mass_invite_to_dialog(
        self,
        group: str = "active_appeals",
        custom_message: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """
        Send invitations to dialog to a group of users.

        Args:
            group: Target group
            custom_message: Optional custom message template
            limit: Max invitations

        Returns:
            Result dict with stats
        """
        return await self.sender.mass_invite(
            group, custom_message, limit
        )

    async def send_feedback_request(
        self,
        admin_identifier: str | int,
        topic: str,
        question: str,
    ) -> dict[str, Any]:
        """
        Send a feedback request to a specific admin.

        Args:
            admin_identifier: @username or telegram_id of admin
            topic: Topic of the feedback request
            question: Specific question to ask

        Returns:
            Result dict with status
        """
        return await self.sender.send_feedback_request(
            admin_identifier, topic, question
        )

    async def broadcast_to_admins(
        self,
        message_text: str,
        request_feedback: bool = True,
    ) -> dict[str, Any]:
        """
        Broadcast message to all active admins.

        Args:
            message_text: Message to send
            request_feedback: Whether to add feedback prompt

        Returns:
            Result dict with stats
        """
        return await self.sender.broadcast_to_admins(
            message_text, request_feedback
        )
