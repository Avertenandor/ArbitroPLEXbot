"""
Async runner for dramatiq tasks.

Provides a thread-safe way to run async code in dramatiq actors.
Solves the event loop issues with SQLAlchemy and Redis connections.
"""

import asyncio
import threading
from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any, TypeVar

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config.settings import settings

T = TypeVar("T")

# Thread-local storage for event loops
_thread_local = threading.local()


def get_event_loop() -> asyncio.AbstractEventLoop:
    """
    Get or create event loop for current thread.

    Creates a new event loop for each thread and reuses it.
    This prevents "Future attached to a different loop" errors.
    """
    try:
        loop = getattr(_thread_local, "loop", None)
        if loop is None or loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            _thread_local.loop = loop
            logger.debug(f"Created new event loop for thread {threading.current_thread().name}")
        return loop
    except Exception as e:
        logger.warning(f"Error getting event loop: {e}, creating new one")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _thread_local.loop = loop
        return loop


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """
    Run async coroutine in the thread's event loop.

    This is the recommended way to run async code in dramatiq actors.
    It reuses the same event loop per thread, preventing connection issues.

    Args:
        coro: Async coroutine to run

    Returns:
        Result of the coroutine
    """
    loop = get_event_loop()
    try:
        return loop.run_until_complete(coro)
    except Exception as e:
        logger.exception(f"Error running async coroutine: {e}")
        raise


def async_actor(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T]:
    """
    Decorator to wrap async function for use in dramatiq actor.

    Usage:
        @dramatiq.actor
        @async_actor
        async def my_task():
            await some_async_operation()

    Args:
        func: Async function to wrap

    Returns:
        Synchronous wrapper function
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        coro = func(*args, **kwargs)
        return run_async(coro)
    return wrapper


@asynccontextmanager
async def create_local_session():
    """
    Create a local database session for the current event loop.

    This creates a new engine with NullPool to avoid connection pool issues
    when running in dramatiq workers with multiple threads.

    Usage:
        async with create_local_session() as session:
            # Use session
            await session.execute(...)

    Yields:
        AsyncSession bound to the current event loop
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

    try:
        async with local_session_maker() as session:
            yield session
    finally:
        await local_engine.dispose()


async def cleanup_connections() -> None:
    """
    Clean up database and redis connections for current session.

    Call this at the end of async tasks to properly close connections.
    """
    from app.config.database import async_engine

    try:
        # Dispose engine connections for this thread
        await async_engine.dispose()
        logger.debug("Database connections cleaned up")
    except Exception as e:
        logger.warning(f"Error cleaning up connections: {e}")
