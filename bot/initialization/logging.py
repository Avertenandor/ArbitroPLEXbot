"""
Bot Initialization - Logging Module.

Module: logging.py
Configures loguru logger for the bot.
Sets up log rotation and retention policies.
"""

from loguru import logger


def setup_logging() -> None:
    """Configure logger with file rotation."""
    logger.add(
        "logs/bot.log",
        rotation="1 day",
        retention="7 days",
        level="INFO",
        encoding="utf-8",
    )

    logger.info("Starting ArbitroPLEXbot Bot...")
