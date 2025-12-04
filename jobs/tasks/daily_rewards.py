"""
Daily rewards task.

Processes daily reward sessions for all confirmed deposits.
Runs once per day to calculate and distribute rewards.
"""

import asyncio

import dramatiq
from loguru import logger

try:
    import redis.asyncio as redis
except ImportError:
    redis = None  # type: ignore

from app.config.database import async_session_maker
from app.config.settings import settings
from app.services.reward_service import RewardService
from app.utils.distributed_lock import DistributedLock


@dramatiq.actor(max_retries=3, time_limit=120_000)  # 2 min timeout (must be > lock timeout)
def process_daily_rewards(session_id: int | None = None) -> None:
    """
    Process daily rewards for active session.

    Calculates rewards for all eligible deposits based on reward session
    configuration. Respects ROI cap (500% for level 1) and earnings_blocked
    flag.

    Args:
        session_id: Specific session ID to process (optional)
    """
    logger.info(
        f"Starting daily rewards processing"
        f"{f' for session {session_id}' if session_id else ''}..."
    )

    try:
        # Run async code
        result = asyncio.run(_process_daily_rewards_async(session_id))

        if result["success"]:
            logger.info(
                f"Daily rewards processing complete: "
                f"{result['rewards_calculated']} rewards calculated, "
                f"total: {result['total_amount']} USDT"
            )
        else:
            logger.error(
                f"Daily rewards processing failed: {result.get('error')}"
            )

    except Exception as e:
        logger.exception(f"Daily rewards processing failed: {e}")


async def _process_daily_rewards_async(
    session_id: int | None,
) -> dict:
    """Async implementation of daily rewards processing."""
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

    # Use distributed lock to prevent concurrent reward processing
    lock = DistributedLock(redis_client=redis_client)

    # Use different lock keys for specific session vs all sessions
    lock_key = f"daily_rewards_session_{session_id}" if session_id else "daily_rewards_processing"

    async with lock.lock(lock_key, timeout=60):
        try:
            async with async_session_maker() as session:
                reward_service = RewardService(session)

                # If session_id provided, process that session
                if session_id:
                    (
                        success,
                        calculated,
                        total,
                        error,
                    ) = await reward_service.calculate_rewards_for_session(session_id)

                    return {
                        "success": success,
                        "rewards_calculated": calculated,
                        "total_amount": float(total),
                        "error": error,
                    }

                # Otherwise, process all active sessions
                active_sessions = await reward_service.get_active_sessions()

                if not active_sessions:
                    logger.info("No active reward sessions found")
                    return {
                        "success": True,
                        "rewards_calculated": 0,
                        "total_amount": 0,
                    }

                total_calculated = 0
                total_amount_sum = 0.0

                for session_obj in active_sessions:
                    (
                        success,
                        calculated,
                        total,
                        error,
                    ) = await reward_service.calculate_rewards_for_session(
                        session_obj.id
                    )

                    if success:
                        total_calculated += calculated
                        total_amount_sum += float(total)
                    else:
                        logger.error(
                            f"Failed to process session {session_obj.id}: {error}"
                        )

                return {
                    "success": True,
                    "rewards_calculated": total_calculated,
                    "total_amount": total_amount_sum,
                }
        finally:
            # Close Redis client
            if redis_client:
                await redis_client.close()
