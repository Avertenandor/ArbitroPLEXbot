"""
Dramatiq broker configuration.

Redis-based message broker for task queue.
"""

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import CurrentMessage, Retries, ShutdownNotifications
from loguru import logger

from app.config.settings import settings

# Initialize Redis broker with graceful shutdown middleware
redis_broker = RedisBroker(
    host=settings.redis_host,
    port=settings.redis_port,
    password=settings.redis_password if settings.redis_password else None,
    db=settings.redis_db,
)

# Add middleware for graceful shutdown, monitoring, and retries
# ShutdownNotifications: Allows workers to gracefully shutdown
# CurrentMessage: Provides access to current message in actors
# Retries: Exponential backoff for failed tasks
redis_broker.add_middleware(ShutdownNotifications())
redis_broker.add_middleware(CurrentMessage())
redis_broker.add_middleware(
    Retries(
        max_retries=3,
        min_backoff=1000,  # 1 second
        max_backoff=60000,  # 1 minute
        retry_when=lambda retries_so_far, exception: retries_so_far < 3,
    )
)

# Set as default broker
dramatiq.set_broker(redis_broker)

# Export broker
broker = redis_broker

logger.info(
    f"Dramatiq broker initialized with graceful shutdown support: "
    f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
)
logger.info(
    "Middleware enabled: ShutdownNotifications, CurrentMessage, "
    "Retries (exponential backoff)"
)
