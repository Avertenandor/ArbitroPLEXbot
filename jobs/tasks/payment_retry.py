"""
Payment retry task (PART5 critical).

Processes pending payment retries with exponential backoff.
Runs every minute to check for retries ready for processing.
"""

import asyncio

import dramatiq
from loguru import logger

try:
    import redis.asyncio as redis
except ImportError:
    redis = None  # type: ignore

from app.config.settings import settings
from app.services.blockchain_service import get_blockchain_service
from app.services.payment_retry_service import PaymentRetryService
from app.utils.distributed_lock import DistributedLock


@dramatiq.actor(max_retries=3, time_limit=300_000)  # 5 min timeout
def process_payment_retries() -> None:
    """
    Process pending payment retries.

    PART5 critical: Ensures failed payments are retried with exponential
    backoff (1min, 2min, 4min, 8min, 16min) and moved to DLQ after 5
    attempts.
    """
    logger.info("Starting payment retry processing...")

    try:
        asyncio.run(_process_payment_retries_async())
        logger.info("Payment retry processing complete")

    except Exception as e:
        logger.exception(f"Payment retry processing failed: {e}")


async def _process_payment_retries_async() -> None:
    """Async implementation of payment retry processing."""
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

    # Use distributed lock to prevent concurrent retry processing
    lock = DistributedLock(redis_client=redis_client)

    async with lock.lock("payment_retry_processing", timeout=300):
        try:
            # Use global engine instead of creating new one
            from app.config.database import async_engine, async_session_maker

            async with async_session_maker() as session:
                # Get blockchain service
                blockchain_service = get_blockchain_service()

                # Process retries
                retry_service = PaymentRetryService(session)
                await retry_service.process_pending_retries(
                    blockchain_service
                )

        finally:
            # Close Redis client
            if redis_client:
                await redis_client.close()
