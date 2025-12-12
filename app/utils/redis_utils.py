"""Redis connection utilities.

Provides helper functions for creating Redis connections with configuration
from settings to avoid code duplication.
"""

import redis.asyncio as redis

from app.config.settings import settings


async def get_redis_client() -> redis.Redis:
    """
    Create and return a Redis client with settings from config.

    Returns:
        redis.Redis: Configured Redis client with decode_responses=True

    Example:
        >>> redis_client = await get_redis_client()
        >>> await redis_client.set("key", "value")
        >>> await redis_client.close()
    """
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password,
        db=settings.redis_db,
        decode_responses=True,
    )


def get_redis_url() -> str:
    """
    Build Redis URL from settings.

    Returns:
        str: Redis connection URL in format redis://[:[password]@]host:port/db

    Example:
        >>> url = get_redis_url()
        >>> # Returns: "redis://:password@localhost:6379/0"
    """
    if settings.redis_password:
        return f"redis://:{settings.redis_password}@{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
    return f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
