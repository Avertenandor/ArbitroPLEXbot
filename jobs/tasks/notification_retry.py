"""
Notification retry task (PART5 critical).

Processes failed notification retries with exponential backoff.
Runs every minute to check for notifications ready for retry.
"""

import dramatiq
from aiogram import Bot
from loguru import logger

try:
    import redis.asyncio as redis
except ImportError:
    redis = None  # type: ignore

from app.config.database import async_session_maker
from app.config.settings import settings
from app.services.notification_retry_service import (
    NotificationRetryService,
)
from app.utils.distributed_lock import DistributedLock
from jobs.async_runner import run_async


@dramatiq.actor(max_retries=3, time_limit=300_000)  # 5 min timeout
def process_notification_retries() -> None:
    """
    Process failed notification retries.

    PART5 critical: Ensures failed notifications are retried with
    exponential backoff (1min, 5min, 15min, 1h, 2h) up to 5 attempts.
    """
    logger.info("Starting notification retry processing...")

    try:
        # Run async code using thread-safe runner
        result = run_async(_process_notification_retries_async())

        logger.info(
            f"Notification retry processing complete: "
            f"{result['successful']} successful, "
            f"{result['failed']} failed, "
            f"{result['gave_up']} gave up"
        )

    except Exception as e:
        logger.exception(f"Notification retry processing failed: {e}")


async def _process_notification_retries_async() -> dict:
    """Async implementation of notification retry processing."""
    # Create Redis client for distributed lock
    redis_client = None
    if redis:
        try:
            redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                db=settings.redis_db,
                decode_responses=True,
            )
        except Exception as e:
            logger.warning(f"Failed to create Redis client for lock: {e}")

    # Use distributed lock to prevent concurrent notification retry processing
    lock = DistributedLock(redis_client=redis_client)

    async with lock.lock("notification_retry_processing", timeout=300):
        try:
            # Use global session maker
            async with async_session_maker() as session:
                # Create bot instance
                bot = Bot(token=settings.telegram_bot_token)
                try:
                    # Process retries
                    retry_service = NotificationRetryService(session, bot)
                    result = await retry_service.process_pending_retries()

                    return result
                finally:
                    # Close bot session
                    await bot.session.close()
        finally:
            # Close Redis client
            if redis_client:
                await redis_client.close()
