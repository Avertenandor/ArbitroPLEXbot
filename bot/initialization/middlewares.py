"""
Bot Initialization - Middlewares Module.

Module: middlewares.py
Registers all bot middlewares in the correct order.
Order is critical for proper request processing.
"""

from aiogram import Dispatcher
from loguru import logger

from app.config.database import async_session_maker
from bot.middlewares.admin_auth_middleware import AdminAuthMiddleware
from bot.middlewares.auth import AuthMiddleware
from bot.middlewares.ban_middleware import BanMiddleware
from bot.middlewares.database import DatabaseMiddleware
from bot.middlewares.error_handler import ErrorHandlerMiddleware
from bot.middlewares.logger_middleware import LoggerMiddleware
from bot.middlewares.menu_state_clear import MenuStateClearMiddleware
from bot.middlewares.message_log_middleware import MessageLogMiddleware
from bot.middlewares.rate_limit_middleware import RateLimitMiddleware
from bot.middlewares.redis_middleware import RedisMiddleware
from bot.middlewares.request_id import RequestIDMiddleware


def register_middlewares(dp: Dispatcher, redis_client) -> None:
    """
    Register all middlewares.

    Middleware order is critical:
    1. RequestID (PART5: must be first)
    2. Error handler
    3. Logger
    4. Rate limiting (BEFORE Database to reduce DB load on spam)
    5. Database
    6. Redis (if available)
    7. Button spam protection (if Redis available)
    8. Session (if Redis available)
    9. Menu state clear
    10. Auth
    11. Ban
    12. Message logging

    Args:
        dp: Dispatcher instance
        redis_client: Redis client (can be None)
    """
    # PART5: RequestID must be first!
    dp.update.middleware(RequestIDMiddleware())

    # Global Error Handler
    dp.update.middleware(ErrorHandlerMiddleware())

    dp.update.middleware(LoggerMiddleware())

    # Rate limiting (optional, requires Redis) - BEFORE Database
    # This prevents spam requests from hitting the database
    # R11-2: RateLimitMiddleware now supports fallback to in-memory counters
    try:
        dp.update.middleware(
            RateLimitMiddleware(
                redis_client=redis_client,  # Can be None for in-memory fallback
                user_limit=30,  # requests per window
                user_window=60,  # seconds
            )
        )
        if redis_client:
            logger.info("Rate limiting enabled with Redis (before Database)")
        else:
            logger.info("Rate limiting enabled with in-memory fallback (before Database)")
    except Exception as e:
        logger.warning(f"Rate limiting disabled: {e}")

    dp.update.middleware(DatabaseMiddleware(session_pool=async_session_maker))

    # Add Redis client to data for handlers that need it
    if redis_client:
        dp.update.middleware(RedisMiddleware(redis_client=redis_client))
        # R13-2: Button spam protection (requires Redis)
        from bot.middlewares.button_spam_protection import (
            ButtonSpamProtectionMiddleware,
        )
        dp.update.middleware(
            ButtonSpamProtectionMiddleware(redis_client=redis_client)
        )

        # Pay-to-Use Authorization Middleware
        from bot.middlewares.session_middleware import SessionMiddleware
        dp.update.middleware(SessionMiddleware(redis=redis_client))

    # Menu state clear must be after DatabaseMiddleware (needs session)
    # but before AuthMiddleware to clear state early
    dp.update.middleware(MenuStateClearMiddleware())
    dp.update.middleware(AuthMiddleware())
    dp.update.middleware(BanMiddleware())
    # Message logging must be after Auth (to get user_id) and Ban (to not log banned users)
    dp.update.middleware(MessageLogMiddleware())

    # Activity logging - ВРЕМЕННО ОТКЛЮЧЕНО до создания таблицы
    # from bot.middlewares.activity_logging import ActivityLoggingMiddleware
    # dp.update.middleware(ActivityLoggingMiddleware())

    logger.info("Middlewares registered successfully")
