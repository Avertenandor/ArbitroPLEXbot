"""Broadcast operations for AI Broadcast Service."""

from typing import Any

from aiogram import Bot
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_broadcast.broadcast_helpers import BroadcastHelpers
from app.services.ai_broadcast.message_formatter import (
    MessageFormatter,
)
from app.services.ai_broadcast.targeting import UserTargeting
from app.services.ai_broadcast.telegram_error_handler import (
    TelegramErrorHandler,
)


class BroadcastService:
    """Handles broadcast operations to groups and admins."""

    def __init__(
        self,
        session: AsyncSession,
        bot: Bot,
        targeting: UserTargeting,
        error_handler: TelegramErrorHandler,
        formatter: MessageFormatter,
        helpers: BroadcastHelpers,
    ):
        self.session = session
        self.bot = bot
        self.targeting = targeting
        self.error_handler = error_handler
        self.formatter = formatter
        self.helpers = helpers

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
        try:
            # Get user IDs based on group
            user_ids = await self.targeting.get_users_by_group(
                group, limit
            )

            if not user_ids:
                return {
                    "success": False,
                    "error": f"Нет пользователей в группе '{group}'",
                    "total": 0,
                }

            # Send messages with rate limiting
            success, failed, failed_users = (
                await self.helpers.broadcast_messages(
                    user_ids, message_text, parse_mode
                )
            )

            logger.info(
                f"ARIA broadcast to '{group}': "
                f"{success} sent, {failed} failed"
            )

            return {
                "success": True,
                "group": group,
                "total": len(user_ids),
                "sent": success,
                "failed": failed,
                "failed_details": failed_users[:5] if failed_users else [],
                "message": self.formatter.format_broadcast_result(
                    group, len(user_ids), success, failed
                ),
            }

        except Exception as e:
            return self.error_handler.handle_broadcast_error(
                e, group, "broadcast"
            )

    async def mass_invite(
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
        try:
            users = await self.targeting.get_users_details_by_group(
                group, limit
            )

            if not users:
                return {
                    "success": False,
                    "error": f"Нет пользователей в группе '{group}'",
                }

            success, failed = await self.helpers.send_mass_invitations(
                users, custom_message
            )

            logger.info(
                f"ARIA mass invite to '{group}': "
                f"{success} sent, {failed} failed"
            )

            return {
                "success": True,
                "group": group,
                "total": len(users),
                "sent": success,
                "failed": failed,
                "message": self.formatter.format_mass_invite_result(
                    group, len(users), success, failed
                ),
            }

        except Exception as e:
            return self.error_handler.handle_broadcast_error(
                e, group, "mass invite"
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
        from app.models import Admin

        try:
            # Get all active admins
            stmt = select(Admin).where(
                Admin.is_active == True  # noqa: E712
            )
            result = await self.session.execute(stmt)
            admins = result.scalars().all()

            if not admins:
                return {
                    "success": False,
                    "error": "Нет активных админов",
                }

            # Add feedback prompt if requested
            if request_feedback:
                message_text = self.formatter.add_feedback_prompt(
                    message_text
                )

            sent_count, failed_count, sent_to = (
                await self.helpers.send_to_admins(admins, message_text)
            )

            logger.info(
                f"ARIA broadcast to {sent_count} admins: "
                f"{', '.join(sent_to)}"
            )

            return {
                "success": True,
                "sent": sent_count,
                "failed": failed_count,
                "admins": sent_to,
                "message": self.formatter.format_admin_broadcast_result(
                    sent_count
                ),
            }

        except Exception as e:
            return self.error_handler.handle_broadcast_error(
                e, "admins", "admin broadcast"
            )
