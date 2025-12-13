"""Helper functions for broadcast operations."""

import asyncio
from typing import Any

from aiogram import Bot
from loguru import logger

from app.services.ai_broadcast.message_formatter import (
    MessageFormatter,
)
from app.services.ai_broadcast.telegram_error_handler import (
    TelegramErrorHandler,
)


class BroadcastHelpers:
    """Helper methods for broadcasting messages."""

    def __init__(
        self,
        bot: Bot,
        error_handler: TelegramErrorHandler,
        formatter: MessageFormatter,
    ):
        self.bot = bot
        self.error_handler = error_handler
        self.formatter = formatter

    async def broadcast_messages(
        self,
        user_ids: list[int],
        message_text: str,
        parse_mode: str,
    ) -> tuple[int, int, list[dict[str, Any]]]:
        """
        Send messages to multiple users with rate limiting.

        Args:
            user_ids: List of user telegram IDs
            message_text: Message to send
            parse_mode: Parse mode for message

        Returns:
            Tuple of (success_count, failed_count, failed_users)
        """
        success = 0
        failed = 0
        failed_users = []

        for user_id in user_ids:
            send_success, error = (
                await self.error_handler.send_with_error_handling(
                    self.bot.send_message,
                    user_id,
                    message_text,
                    parse_mode=parse_mode,
                )
            )

            if send_success:
                success += 1
            else:
                failed += 1
                self.error_handler.log_send_result(
                    False, error, user_id, "broadcast message"
                )
                failed_users.append(
                    {"user_id": user_id, "error": str(error)}
                )

            # Rate limit: 20 msg/sec to avoid Telegram limits
            await asyncio.sleep(0.05)

        return success, failed, failed_users

    async def send_mass_invitations(
        self,
        users: list[dict[str, Any]],
        custom_message: str | None,
    ) -> tuple[int, int]:
        """
        Send invitations to multiple users.

        Args:
            users: List of user data dictionaries
            custom_message: Optional custom message template

        Returns:
            Tuple of (success_count, failed_count)
        """
        success = 0
        failed = 0

        for user_data in users:
            user_name = (
                user_data.get("username")
                or user_data.get("first_name")
                or None
            )

            message = self.formatter.format_mass_invitation(
                user_name, custom_message
            )

            send_success, error = (
                await self.error_handler.send_with_error_handling(
                    self.bot.send_message,
                    user_data["telegram_id"],
                    message,
                    parse_mode="Markdown",
                )
            )

            if send_success:
                success += 1
            else:
                failed += 1
                self.error_handler.log_send_result(
                    False,
                    error,
                    user_data["telegram_id"],
                    "invitation",
                )

            await asyncio.sleep(0.05)

        return success, failed

    async def send_to_admins(
        self,
        admins: list[Any],
        message_text: str,
    ) -> tuple[int, int, list[str]]:
        """
        Send message to multiple admins.

        Args:
            admins: List of Admin objects
            message_text: Message to send

        Returns:
            Tuple of (sent_count, failed_count, sent_to_usernames)
        """
        sent_count = 0
        failed_count = 0
        sent_to = []

        for admin in admins:
            send_success, error = (
                await self.error_handler.send_with_error_handling(
                    self.bot.send_message,
                    admin.telegram_id,
                    message_text,
                    parse_mode="Markdown",
                )
            )

            if send_success:
                sent_count += 1
                sent_to.append(f"@{admin.username}")
            else:
                failed_count += 1
                self.error_handler.log_send_result(
                    False,
                    error,
                    admin.telegram_id,
                    "admin message",
                )

            await asyncio.sleep(0.1)  # Rate limiting

        return sent_count, failed_count, sent_to
