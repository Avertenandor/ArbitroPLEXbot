"""
Bot Initialization - Storage Module.

Module: storage.py
Sets up FSM storage (Redis with PostgreSQL fallback).
Handles Redis connection failures gracefully.
"""

from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.redis import RedisStorage
from loguru import logger


try:
    from redis.asyncio import Redis as AsyncRedis
except ImportError:
    # Fallback for older redis versions
    import redis.asyncio as aioredis

    AsyncRedis = aioredis.Redis

from app.config.settings import settings


async def setup_fsm_storage() -> tuple[BaseStorage, AsyncRedis | None]:
    """
    Set up FSM storage with Redis (fallback to PostgreSQL).

    Returns:
        Tuple of (storage, redis_client)
    """
    redis_client = None
    try:
        redis_client = AsyncRedis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
            decode_responses=True,
        )
        # Test Redis connection
        await redis_client.ping()
        logger.info("Redis connection established for FSM storage")
        storage = RedisStorage(redis=redis_client)
        return storage, redis_client
    except Exception as e:
        logger.error(f"Failed to initialize Redis storage: {e}")
        logger.warning(
            "R11-3: Falling back to PostgreSQL FSM storage (states will persist)"
        )
        from bot.storage.postgresql_fsm_storage import PostgreSQLFSMStorage

        storage = PostgreSQLFSMStorage()
        return storage, None
