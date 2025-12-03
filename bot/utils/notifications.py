"""
Notification utilities.

Helper functions for sending notifications.
"""

import asyncio

from aiogram import Bot
from loguru import logger

from app.config.constants import TELEGRAM_TIMEOUT


async def notify_admins(
    bot: Bot,
    admin_ids: list[int],
    message: str,
    parse_mode: str = "Markdown",
) -> None:
    """
    Send notification to all admins.

    Args:
        bot: Bot instance
        admin_ids: List of admin Telegram IDs
        message: Message to send
        parse_mode: Parse mode (Markdown, HTML)
    """
    for admin_id in admin_ids:
        try:
            await asyncio.wait_for(
                bot.send_message(
                    admin_id,
                    message,
                    parse_mode=parse_mode,
                ),
                timeout=TELEGRAM_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.error(f"Timeout notifying admin {admin_id}")
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")
