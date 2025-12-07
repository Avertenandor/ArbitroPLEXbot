"""
Admin session cleanup task.

Cleans up expired and inactive admin sessions.
Runs every 5 minutes to deactivate expired sessions.
"""

import dramatiq
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

try:
    import redis.asyncio as redis
except ImportError:
    redis = None  # type: ignore

from app.config.settings import settings
from app.repositories.admin_session_repository import AdminSessionRepository
from app.utils.distributed_lock import DistributedLock
from jobs.async_runner import run_async


@dramatiq.actor(max_retries=3, time_limit=60_000)  # 1 min timeout
def cleanup_expired_admin_sessions() -> dict:
    """
    Cleanup expired and inactive admin sessions.

    Deactivates:
    - Expired sessions (expires_at < now)
    - Inactive sessions (no activity > 15 minutes)

    Returns:
        Dict with cleaned_up count
    """
    logger.info("Starting admin session cleanup...")

    try:
        # Run async code using thread-safe runner
        result = run_async(_cleanup_sessions_async())

        logger.info(
            f"Admin session cleanup complete: "
            f"{result['cleaned_up']} sessions deactivated"
        )

        return result

    except Exception as e:
        logger.exception(f"Admin session cleanup failed: {e}")
        return {"cleaned_up": 0}


async def _cleanup_sessions_async() -> dict:
    """
    Async implementation of session cleanup.

    Returns:
        Dict with cleaned_up count
    """
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
            redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                db=settings.redis_db,
                decode_responses=True,
            )
        except Exception as e:
            logger.warning(f"Failed to create Redis client for lock: {e}")

    # Use distributed lock to prevent concurrent cleanup
    lock = DistributedLock(redis_client=redis_client)

    try:
        async with lock.lock("admin_session_cleanup", timeout=30):
            async with local_session_maker() as session:
                session_repo = AdminSessionRepository(session)

                # Cleanup expired sessions
                expired_count = await session_repo.cleanup_expired_sessions()

                # Cleanup inactive sessions (no activity > 15 minutes)
                from datetime import UTC, datetime, timedelta

                from sqlalchemy import select

                from app.models.admin_session import AdminSession

                now = datetime.now(UTC)
                inactivity_threshold = now - timedelta(minutes=15)

                stmt = (
                    select(AdminSession)
                    .where(AdminSession.is_active)
                    .where(AdminSession.last_activity < inactivity_threshold)
                )
                result = await session.execute(stmt)
                inactive_sessions = list(result.scalars().all())

                inactive_count = 0
                for sess in inactive_sessions:
                    sess.is_active = False
                    inactive_count += 1

                await session.commit()

                total_cleaned = expired_count + inactive_count

                if total_cleaned > 0:
                    logger.info(
                        f"Cleaned up {expired_count} expired and "
                        f"{inactive_count} inactive admin sessions"
                    )

                return {"cleaned_up": total_cleaned}
    finally:
        # Close Redis client
        if redis_client:
            await redis_client.close()
        # Dispose engine
        await local_engine.dispose()
