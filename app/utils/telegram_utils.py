"""
Telegram bot utility functions.

Provides helpers for creating and managing bot instances.
"""

from typing import Optional

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from loguru import logger


async def get_or_create_bot() -> tuple[Optional[Bot], bool]:
    """
    Get existing bot or create a new one.

    Returns:
        tuple: (bot_instance, should_close)
        - bot_instance: Bot instance or None if creation failed
        - should_close: True if bot was created and needs to close session
    """
    from app.config.settings import settings
    from app.services.bot_provider import get_bot

    bot = get_bot()
    should_close = False

    if not bot:
        try:
            bot = Bot(
                token=settings.telegram_bot_token,
                default=DefaultBotProperties(
                    parse_mode=ParseMode.MARKDOWN
                ),
            )
            should_close = True
        except Exception as e:
            logger.error(f"Failed to create fallback bot instance: {e}")
            return None, False

    return bot, should_close
