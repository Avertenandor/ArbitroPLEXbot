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
    Send notification to all admins in parallel using asyncio.gather.

    Args:
        bot: Bot instance
        admin_ids: List of admin Telegram IDs
        message: Message to send
        parse_mode: Parse mode (Markdown, HTML)
    """
    if not admin_ids:
        logger.warning("No admin IDs provided for notification")
        return

    async def send_to_admin(admin_id: int) -> tuple[int, bool]:
        """Send message to single admin."""
        try:
            await asyncio.wait_for(
                bot.send_message(
                    admin_id,
                    message,
                    parse_mode=parse_mode,
                ),
                timeout=TELEGRAM_TIMEOUT,
            )
            return admin_id, True
        except asyncio.TimeoutError:
            logger.error(f"Timeout notifying admin {admin_id}")
            return admin_id, False
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")
            return admin_id, False

    # Send to all admins in parallel
    tasks = [send_to_admin(admin_id) for admin_id in admin_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Count failures
    failed = 0
    for result in results:
        if isinstance(result, Exception):
            failed += 1
            logger.error(f"Admin notification task failed: {result}")
        else:
            _, success = result
            if not success:
                failed += 1

    if failed > 0:
        logger.warning(f"Failed to notify {failed}/{len(admin_ids)} admins")
    else:
        logger.debug(f"Successfully notified all {len(admin_ids)} admins")
