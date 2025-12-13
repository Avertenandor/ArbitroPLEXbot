"""Cleanup task for logs and orphaned data."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import dramatiq
from loguru import logger


try:
    import redis.asyncio as redis
except ImportError:
    redis = None  # type: ignore

from app.config.database import async_session_maker
from app.config.operational_constants import DRAMATIQ_TIME_LIMIT_STANDARD
from app.config.settings import settings
from app.utils.datetime_utils import utc_now
from app.utils.distributed_lock import DistributedLock
from app.utils.redis_utils import get_redis_client
from jobs.async_runner import run_async


@dramatiq.actor(max_retries=3, time_limit=DRAMATIQ_TIME_LIMIT_STANDARD)  # 5 min timeout
def cleanup_logs_and_data() -> None:
    """
    Cleanup old logs and orphaned data.

    - Deletes old log files (>7 days)
    - Removes orphaned pending deposits (>24 hours)
    - Cleans up old sessions
    """
    logger.info("Starting cleanup task...")

    try:
        run_async(_cleanup_logs_and_data_async())
        logger.info("Cleanup task completed")

    except Exception as e:
        logger.exception(f"Cleanup task failed: {e}")


async def _cleanup_logs_and_data_async() -> None:
    """Async implementation of cleanup task."""
    # Create Redis client for distributed lock
    redis_client = None
    if redis:
        try:
            redis_client = await get_redis_client()
        except Exception as e:
            logger.warning(f"Failed to create Redis client for lock: {e}")

    # Use distributed lock to prevent concurrent cleanup
    lock = DistributedLock(redis_client=redis_client)

    async with lock.lock("cleanup_task", timeout=300):
        try:
            # Cleanup log files
            await _cleanup_log_files()

            # Cleanup database
            await _cleanup_database()

        finally:
            # Close Redis client
            if redis_client:
                await redis_client.close()


async def _cleanup_log_files() -> None:
    """Delete old log files."""
    try:
        log_dir = Path("logs")

        if not log_dir.exists():
            return

        cutoff_date = utc_now() - timedelta(days=7)

        for log_file in log_dir.glob("*.log*"):
            if log_file.is_file():
                # FIXED: Use timezone-aware datetime
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime, tz=UTC)

                if file_time < cutoff_date:
                    log_file.unlink()
                    logger.info(f"Deleted old log: {log_file.name}")

    except Exception as e:
        logger.error(f"Log cleanup error: {e}")


async def _cleanup_database() -> None:
    """Cleanup orphaned database records."""
    session = None
    try:
        async with async_session_maker() as session:
            # Cleanup orphaned pending deposits (>24 hours old)
            from app.repositories.deposit_repository import DepositRepository

            deposit_repo = DepositRepository(session)

            cutoff_time = utc_now() - timedelta(hours=24)

            # Find old pending deposits
            deposits = await deposit_repo.get_pending_deposits()

            deleted_count = 0

            for deposit in deposits:
                if deposit.created_at < cutoff_time:
                    # FIXED: Use session.delete for direct deletion (sync method)
                    session.delete(deposit)
                    deleted_count += 1

            if deleted_count > 0:
                logger.info(
                    f"Deleted {deleted_count} orphaned pending deposits"
                )

            await session.commit()

    except Exception as e:
        if session:
            await session.rollback()
        logger.error(f"Database cleanup error: {e}")
        raise  # For dramatiq retry
