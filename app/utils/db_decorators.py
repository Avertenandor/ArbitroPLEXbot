"""
Database decorators for automatic error handling and rollback.

Provides decorators to automatically handle database errors and rollbacks
in async functions that use SQLAlchemy sessions.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession


T = TypeVar("T")


def with_rollback_on_error(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator that automatically rolls back the session on any exception.

    Usage:
        @with_rollback_on_error
        async def my_function(session: AsyncSession, ...):
            # Your database operations
            pass

    The decorator will:
    1. Execute the wrapped function
    2. If an exception occurs, automatically call session.rollback()
    3. Re-raise the exception for proper error handling

    Args:
        func: Async function to wrap. Must accept 'session' as a keyword
              argument or have it as the first positional argument.

    Returns:
        Wrapped function with automatic rollback on error

    Example:
        @with_rollback_on_error
        async def create_user(session: AsyncSession, username: str):
            user = User(username=username)
            session.add(user)
            await session.commit()
            return user
    """
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        # Try to get session from kwargs first
        session = kwargs.get('session')

        # If not in kwargs, try to get from first positional argument
        if session is None and args:
            # Check if first arg is AsyncSession
            if isinstance(args[0], AsyncSession):
                session = args[0]

        # If still no session found, execute without rollback handling
        if session is None:
            logger.warning(
                f"Function {func.__name__} decorated with @with_rollback_on_error "
                f"but no session argument found. Rollback will not be performed."
            )
            return await func(*args, **kwargs)

        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Perform rollback
            try:
                await session.rollback()
                logger.info(
                    f"Rollback performed in {func.__name__} due to error: {type(e).__name__}"
                )
            except Exception as rollback_error:
                logger.error(
                    f"Failed to rollback in {func.__name__}: {rollback_error}",
                    exc_info=True
                )
            # Re-raise original exception
            raise

    return wrapper


def with_auto_commit(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator that automatically commits the session on success and rolls back on error.

    Usage:
        @with_auto_commit
        async def my_function(session: AsyncSession, ...):
            # Your database operations
            # No need to call session.commit() - it's automatic
            pass

    The decorator will:
    1. Execute the wrapped function
    2. If successful, automatically call session.commit()
    3. If an exception occurs, automatically call session.rollback()
    4. Re-raise the exception for proper error handling

    Args:
        func: Async function to wrap. Must accept 'session' as a keyword
              argument or have it as the first positional argument.

    Returns:
        Wrapped function with automatic commit/rollback

    Example:
        @with_auto_commit
        async def update_user_balance(session: AsyncSession, user_id: int, amount: float):
            user = await session.get(User, user_id)
            user.balance += amount
            # Commit happens automatically
    """
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        # Try to get session from kwargs first
        session = kwargs.get('session')

        # If not in kwargs, try to get from first positional argument
        if session is None and args:
            # Check if first arg is AsyncSession
            if isinstance(args[0], AsyncSession):
                session = args[0]

        # If still no session found, execute without commit/rollback handling
        if session is None:
            logger.warning(
                f"Function {func.__name__} decorated with @with_auto_commit "
                f"but no session argument found. Commit/rollback will not be performed."
            )
            return await func(*args, **kwargs)

        try:
            result = await func(*args, **kwargs)
            # Commit on success
            await session.commit()
            logger.debug(f"Auto-commit performed in {func.__name__}")
            return result
        except Exception as e:
            # Rollback on error
            try:
                await session.rollback()
                logger.info(
                    f"Rollback performed in {func.__name__} due to error: {type(e).__name__}"
                )
            except Exception as rollback_error:
                logger.error(
                    f"Failed to rollback in {func.__name__}: {rollback_error}",
                    exc_info=True
                )
            # Re-raise original exception
            raise

    return wrapper
