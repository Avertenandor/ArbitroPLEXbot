"""
Cache invalidation utilities.

Provides functions to invalidate Redis cache when data is updated.
"""

from loguru import logger

try:
    from redis.asyncio import Redis as AsyncRedis
except ImportError:
    import redis.asyncio as aioredis

    AsyncRedis = aioredis.Redis

from app.models.user import User


async def invalidate_deposit_level_cache(
    redis: AsyncRedis, level: int | None = None
) -> None:
    """
    Invalidate deposit level cache.

    Args:
        redis: Redis client instance
        level: Specific level number to invalidate (1-5), or None to invalidate all levels
    """
    try:
        if level is not None:
            # Invalidate specific level
            key = f"deposit_level:{level}:current"
            deleted = await redis.delete(key)
            if deleted:
                logger.info(f"Cache invalidated: {key}")
        else:
            # Invalidate all levels (1-5)
            keys_deleted = 0
            for lvl in range(1, 6):
                key = f"deposit_level:{lvl}:current"
                deleted = await redis.delete(key)
                keys_deleted += deleted
            if keys_deleted:
                logger.info(f"Cache invalidated: {keys_deleted} deposit level(s)")
    except Exception as e:
        logger.error(f"Failed to invalidate deposit level cache: {e}")


async def invalidate_global_settings_cache(redis: AsyncRedis) -> None:
    """
    Invalidate global settings cache.

    Args:
        redis: Redis client instance
    """
    try:
        key = "global_settings"
        deleted = await redis.delete(key)
        if deleted:
            logger.info(f"Cache invalidated: {key}")
    except Exception as e:
        logger.error(f"Failed to invalidate global settings cache: {e}")


async def invalidate_user_cache(
    redis_client: AsyncRedis,
    user_id: int,
    telegram_id: int | None = None,
) -> None:
    """
    Invalidate User cache in Redis.

    Removes cached user data from Redis when user is updated.
    This ensures that the next read will fetch fresh data from database.

    Cache keys invalidated:
    - user:id:{user_id}
    - user:telegram_id:{telegram_id} (if telegram_id provided)

    Args:
        redis_client: Redis client instance
        user_id: User ID
        telegram_id: User's Telegram ID (optional)

    Example:
        >>> from app.utils.redis_utils import get_redis_client
        >>> redis = await get_redis_client()
        >>> await invalidate_user_cache(redis, user_id=123, telegram_id=456789)
        >>> await redis.close()
    """
    if not redis_client:
        logger.warning("Redis client not provided, skipping user cache invalidation")
        return

    try:
        keys_to_delete = [f"user:id:{user_id}"]
        if telegram_id:
            keys_to_delete.append(f"user:telegram_id:{telegram_id}")

        deleted_count = 0
        for key in keys_to_delete:
            result = await redis_client.delete(key)
            if result > 0:
                deleted_count += 1

        if deleted_count > 0:
            logger.debug(
                f"Invalidated {deleted_count} user cache keys for user {user_id}",
                extra={
                    "user_id": user_id,
                    "telegram_id": telegram_id,
                    "keys": keys_to_delete,
                },
            )
    except Exception as e:
        # Don't fail the operation if cache invalidation fails
        logger.warning(
            f"Failed to invalidate user cache for user {user_id}: {e}",
            extra={"user_id": user_id, "telegram_id": telegram_id},
        )


async def invalidate_user_cache_from_model(
    redis_client: AsyncRedis,
    user: User,
) -> None:
    """
    Invalidate User cache using User model instance.

    Convenience wrapper that extracts user_id and telegram_id from User object.

    Args:
        redis_client: Redis client instance
        user: User model instance

    Example:
        >>> user = await user_repo.get_by_id(123)
        >>> await invalidate_user_cache_from_model(redis, user)
    """
    await invalidate_user_cache(
        redis_client=redis_client,
        user_id=user.id,
        telegram_id=user.telegram_id,
    )
