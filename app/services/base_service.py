"""
Base service class.

Provides common functionality for all service classes including session management,
logging, and helper decorators.
"""

import functools
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession


# Type variable for generic decorator return types
T = TypeVar("T")


@dataclass
class ServiceResult:
    """
    Standard service result container.

    Used to return structured results from service methods.
    """
    success: bool
    data: Any = None
    error: str | None = None
    error_code: str | None = None


class BaseService:
    """
    Base service class.

    Provides common functionality for all service classes:
    - Session management
    - Logging with bound service context
    - Transaction helpers
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize base service.

        Args:
            session: Async database session
        """
        self.session = session
        self.logger = logger.bind(service=self.__class__.__name__)

    async def commit(self) -> None:
        """
        Commit current transaction.

        Raises:
            Exception: If commit fails
        """
        await self.session.commit()

    async def rollback(self) -> None:
        """
        Rollback current transaction.

        Raises:
            Exception: If rollback fails
        """
        await self.session.rollback()

    async def refresh(self, obj: Any) -> None:
        """
        Refresh object from database.

        Args:
            obj: SQLAlchemy model instance to refresh

        Raises:
            Exception: If refresh fails
        """
        await self.session.refresh(obj)


def transaction(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to wrap method in transaction with automatic commit/rollback.

    Commits on success, rolls back on exception.

    Usage:
        @transaction
        async def my_service_method(self, ...):
            # Your code here
            pass

    Args:
        func: Async method to wrap

    Returns:
        Wrapped async method
    """
    @functools.wraps(func)
    async def wrapper(self: BaseService, *args: Any, **kwargs: Any) -> Any:
        try:
            result = await func(self, *args, **kwargs)
            await self.commit()
            return result
        except Exception as e:
            await self.rollback()
            self.logger.error(
                f"Transaction failed in {func.__name__}",
                extra={
                    "error": str(e),
                    "function": func.__name__,
                },
                exc_info=True,
            )
            raise

    return wrapper


def log_operation(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to log method entry/exit with timing.

    Logs:
    - Method entry with arguments
    - Method exit with duration
    - Exceptions if any

    Usage:
        @log_operation
        async def my_service_method(self, user_id: int):
            # Your code here
            pass

    Args:
        func: Async method to wrap

    Returns:
        Wrapped async method
    """
    @functools.wraps(func)
    async def wrapper(self: BaseService, *args: Any, **kwargs: Any) -> Any:
        start_time = time.time()

        # Log entry
        self.logger.info(
            f"Starting {func.__name__}",
            extra={
                "function": func.__name__,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys()),
            },
        )

        try:
            result = await func(self, *args, **kwargs)
            duration = time.time() - start_time

            # Log success
            self.logger.info(
                f"Completed {func.__name__}",
                extra={
                    "function": func.__name__,
                    "duration_seconds": round(duration, 3),
                    "success": True,
                },
            )

            return result

        except Exception as e:
            duration = time.time() - start_time

            # Log failure
            self.logger.error(
                f"Failed {func.__name__}",
                extra={
                    "function": func.__name__,
                    "duration_seconds": round(duration, 3),
                    "error": str(e),
                    "success": False,
                },
                exc_info=True,
            )

            raise

    return wrapper
