"""
Bot Initialization - Shutdown Module.

Module: shutdown.py
Handles graceful shutdown of the bot.
Stops scheduler and closes database connections.
"""

from loguru import logger


async def shutdown_handler() -> None:
    """Handle graceful shutdown."""
    logger.info("Graceful shutdown initiated...")

    # Stop scheduler if running
    try:
        from jobs.scheduler import scheduler_instance
        if scheduler_instance and scheduler_instance.running:
            scheduler_instance.shutdown(wait=True)
            logger.info("Scheduler stopped")
    except Exception as e:
        logger.warning(f"Error stopping scheduler: {e}")

    # Close database connections
    try:
        from app.config.database import engine
        await engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.warning(f"Error closing database: {e}")

    logger.info("Graceful shutdown complete")
