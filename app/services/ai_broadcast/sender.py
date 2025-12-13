"""Message sending utilities for AI Broadcast Service."""

import asyncio
from typing import Any

from aiogram import Bot
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
)
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_broadcast.broadcast_helpers import BroadcastHelpers
from app.services.ai_broadcast.broadcast_service import BroadcastService
from app.services.ai_broadcast.invitation_service import (
    InvitationService,
)
from app.services.ai_broadcast.message_formatter import (
    MessageFormatter,
)
from app.services.ai_broadcast.targeting import UserTargeting
from app.services.ai_broadcast.telegram_error_handler import (
    TelegramErrorHandler,
)


class MessageSender:
    """Handles all message sending operations."""

    def __init__(
        self,
        session: AsyncSession,
        bot: Bot,
        targeting: UserTargeting,
    ):
        self.session = session
        self.bot = bot
        self.targeting = targeting
        self.error_handler = TelegramErrorHandler()
        self.formatter = MessageFormatter()
        self.helpers = BroadcastHelpers(
            bot, self.error_handler, self.formatter
        )
        self.invitation = InvitationService(
            bot, targeting, self.error_handler, self.formatter
        )
        self.broadcast = BroadcastService(
            session,
            bot,
            targeting,
            self.error_handler,
            self.formatter,
            self.helpers,
        )

    async def send_to_user(
        self,
        user_identifier: str | int,
        message_text: str,
        admin_telegram_id: int | None = None,
        parse_mode: str = "Markdown",
    ) -> dict[str, Any]:
        """
        Send a single message to a user.

        Args:
            user_identifier: @username, telegram_id, or ID:xxx
            message_text: Message text to send
            admin_telegram_id: Admin who initiated the send
            parse_mode: Markdown or HTML

        Returns:
            Result dict with status
        """
        try:
            # Find user
            user = await self.targeting.find_user(user_identifier)
            if not user:
                return {
                    "success": False,
                    "error": (
                        f"Пользователь '{user_identifier}' не найден"
                    ),
                }

            # Send message
            await self.bot.send_message(
                user.telegram_id,
                message_text,
                parse_mode=parse_mode,
            )

            logger.info(
                f"ARIA (admin {admin_telegram_id}) sent message "
                f"to user {user.telegram_id} (@{user.username})"
            )

            return {
                "success": True,
                "user_id": user.telegram_id,
                "username": user.username,
                "message": "Сообщение успешно отправлено",
            }

        except Exception as e:
            return self.error_handler.handle_send_error(
                e, user_identifier, "sending message"
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
        return await self.broadcast.broadcast_to_group(
            group, message_text, limit, parse_mode
        )

    async def send_invitation(
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
        return await self.invitation.send_invitation(
            user_identifier, custom_message
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
        return await self.broadcast.mass_invite(
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
        return await self.invitation.send_feedback_request(
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
        return await self.broadcast.broadcast_to_admins(
            message_text, request_feedback
        )
