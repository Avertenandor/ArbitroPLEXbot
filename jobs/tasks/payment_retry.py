"""
Payment retry task (PART5 critical).

Processes pending payment retries with exponential backoff.
Runs every minute to check for retries ready for processing.
"""

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
from app.utils.redis_utils import get_redis_client
from jobs.async_runner import run_async


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
        run_async(_process_payment_retries_async())
        logger.info("Payment retry processing complete")

    except Exception as e:
        logger.exception(f"Payment retry processing failed: {e}")


async def _process_payment_retries_async() -> None:
    """Async implementation of payment retry processing."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    # Create a local engine with NullPool to avoid connection pool lock issues
    local_engine = create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=NullPool,
    )

    local_session_maker = async_sessionmaker(
        local_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    # Create Redis client for distributed lock
    redis_client = None
    if redis:
        try:
            redis_client = await get_redis_client()
        except Exception as e:
            logger.warning(f"Failed to create Redis client for lock: {e}")

    # Use distributed lock to prevent concurrent retry processing
    lock = DistributedLock(redis_client=redis_client)

    try:
        async with lock.lock("payment_retry_processing", timeout=300):
            async with local_session_maker() as session:
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
        # Dispose engine
        await local_engine.dispose()
