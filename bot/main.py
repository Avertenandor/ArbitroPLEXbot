"""
Bot main entry point.

Initializes and runs the Telegram bot with aiogram 3.x.

This refactored version delegates initialization to modular components
in the bot/initialization/ directory for better organization and maintainability.
"""

import asyncio
import sys
import warnings
from pathlib import Path


# Suppress eth_utils network warnings about invalid ChainId
# These warnings are from eth_utils library initialization and don't affect functionality
# Must be set BEFORE importing any modules that use eth_utils
warnings.filterwarnings(
    "ignore",
    message=".*does not have a valid ChainId.*",
    category=UserWarning,
    module="eth_utils.network",
)
# Also suppress warnings from any module that may import eth_utils
warnings.filterwarnings(
    "ignore",
    message=".*does not have a valid ChainId.*",
    category=UserWarning,
)

from aiogram import Bot, Dispatcher  # noqa: E402
from aiogram.client.default import DefaultBotProperties  # noqa: E402
from aiogram.types import ErrorEvent  # noqa: E402
from loguru import logger  # noqa: E402


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.database import async_session_maker  # noqa: E402
from app.config.settings import settings  # noqa: E402
from app.utils.admin_init import ensure_default_super_admin  # noqa: E402

# Import initialization modules
from bot.initialization.handlers import register_all_handlers  # noqa: E402
from bot.initialization.logging import setup_logging  # noqa: E402
from bot.initialization.middlewares import register_middlewares  # noqa: E402
from bot.initialization.services import initialize_all_services  # noqa: E402
from bot.initialization.shutdown import shutdown_handler  # noqa: E402
from bot.initialization.storage import setup_fsm_storage  # noqa: E402


# Global bot instance for external access (e.g. from services)
bot_instance: Bot | None = None


async def main() -> None:  # noqa: C901
    """Initialize and run the bot."""
    # Configure logger
    setup_logging()

    # Initialize services (encryption, blockchain, validation)
    initialize_all_services()

    # Initialize FSM storage (Redis with PostgreSQL fallback)
    storage, redis_client = await setup_fsm_storage()

    # Initialize bot
    # ВАЖНО: не используем глобальный Markdown по умолчанию, чтобы
    # динамические тексты с подчёркиваниями/ссылками не ломали разметку.
    # Там, где нужен Markdown или HTML, он указывается явно в хендлерах.
    global bot_instance
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(),  # без parse_mode по умолчанию
    )
    bot_instance = bot

    # Register bot provider for dependency injection (avoid circular imports)
    from app.services.bot_provider import set_bot_getter
    set_bot_getter(lambda: bot_instance)

    # Initialize dispatcher with storage
    dp = Dispatcher(storage=storage)

    # Register middlewares (order matters!)
    register_middlewares(dp, redis_client)

    # Register global error handler (MUST BE FIRST)
    @dp.error()
    async def error_handler(event: ErrorEvent) -> bool:
        """Global error handler for unhandled exceptions."""
        logger.exception(
            f"Unhandled error in bot: {event.exception.__class__.__name__}: {event.exception}",
            extra={"update": str(event.update) if event.update else None},
        )

        # Try to send error message to user
        try:
            if event.update and event.update.message:
                await event.update.message.answer(
                    "⚠️ Произошла ошибка. Пожалуйста, попробуйте позже или обратитесь в поддержку."
                )
        except Exception as send_error:
            logger.error(f"Failed to send error message: {send_error}")

        return True  # Mark error as handled

    # Register all handlers (user, admin, fallback)
    register_all_handlers(dp)

    # Test bot connection
    try:
        bot_info = await bot.get_me()
        logger.info(f"Bot connected: @{bot_info.username} (ID: {bot_info.id})")

        # Set bot username in settings if not already set
        import os

        if not settings.telegram_bot_username:
            os.environ["TELEGRAM_BOT_USERNAME"] = bot_info.username
            # Update settings object (runtime override)
            settings.telegram_bot_username = bot_info.username
            logger.info(f"Set bot username to: {bot_info.username}")
    except Exception as e:
        logger.error(f"Failed to connect to Telegram API: {e}")
        raise

    # Initialize default super admin (after bot connection is established)
    logger.info("Initializing default super admin...")
    try:
        async with async_session_maker() as session:
            await ensure_default_super_admin(session, bot=bot)
        logger.info("Default super admin initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize default super admin: {e}")
        logger.warning("Bot will continue, but admin may need to be created manually")

    # Start polling
    logger.info("Bot started successfully")

    # Start health check server in background
    try:
        from app.http_health_server import run_health_server

        def _handle_health_server_error(task: asyncio.Task) -> None:
            """Log errors from health server task."""
            try:
                if task.cancelled():
                    return
                exc = task.exception()
                if exc:
                    logger.error(f"Health server task failed: {exc}")
            except asyncio.CancelledError:
                pass

        health_task = asyncio.create_task(
            run_health_server(
                host="0.0.0.0",
                port=settings.health_check_port or 8080,
            )
        )
        health_task.add_done_callback(_handle_health_server_error)
        logger.info(
            f"Health check server started on port "
            f"{settings.health_check_port or 8080}"
        )
    except Exception as e:
        logger.warning(f"Failed to start health check server: {e}")

    # Graceful shutdown event

    try:
        logger.info("Starting polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.exception(f"Polling error: {e}")
        raise
    finally:
        await shutdown_handler()
        if redis_client:
            await redis_client.aclose()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (KeyboardInterrupt)")
    except Exception as e:
        logger.exception(f"Bot crashed: {e}")
        sys.exit(1)
