"""Invitation and feedback request service."""

from typing import Any

from aiogram import Bot
from loguru import logger

from app.services.ai_broadcast.message_formatter import (
    MessageFormatter,
)
from app.services.ai_broadcast.targeting import UserTargeting
from app.services.ai_broadcast.telegram_error_handler import (
    TelegramErrorHandler,
)


class InvitationService:
    """Handles invitation and feedback request operations."""

    def __init__(
        self,
        bot: Bot,
        targeting: UserTargeting,
        error_handler: TelegramErrorHandler,
        formatter: MessageFormatter,
    ):
        self.bot = bot
        self.targeting = targeting
        self.error_handler = error_handler
        self.formatter = formatter

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
        user = await self.targeting.find_user(user_identifier)
        if not user:
            return {
                "success": False,
                "error": (
                    f"Пользователь '{user_identifier}' не найден"
                ),
            }

        # Format invitation message
        user_name = user.username or user.first_name
        message = self.formatter.format_invitation(
            user_name, custom_message
        )

        try:
            await self.bot.send_message(
                user.telegram_id,
                message,
                parse_mode="Markdown",
            )

            logger.info(
                f"ARIA sent invitation to user "
                f"{user.telegram_id} (@{user.username})"
            )

            return {
                "success": True,
                "user_id": user.telegram_id,
                "username": user.username,
                "message": "Приглашение успешно отправлено",
            }

        except Exception as e:
            return self.error_handler.handle_send_error(
                e, user_identifier, "sending invitation"
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
        try:
            # Find admin
            admin = await self.targeting.find_admin(admin_identifier)
            if not admin:
                return {
                    "success": False,
                    "error": f"Админ '{admin_identifier}' не найден",
                }

            # Format feedback request message
            message = self.formatter.format_feedback_request(
                topic, question
            )

            await self.bot.send_message(
                admin.telegram_id,
                message,
                parse_mode="Markdown",
            )

            logger.info(
                f"ARIA sent feedback request to admin "
                f"{admin.telegram_id} (@{admin.username}) "
                f"on topic: {topic}"
            )

            return {
                "success": True,
                "admin_id": admin.telegram_id,
                "admin_username": admin.username,
                "topic": topic,
                "message": f"Запрос отправлен @{admin.username}",
            }

        except Exception as e:
            return self.error_handler.handle_send_error(
                e, admin_identifier, "sending feedback request"
            )
