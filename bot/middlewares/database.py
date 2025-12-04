"""
Database middleware.

Provides database session factory to handlers for proper transaction management.
Session lifecycle is controlled by handlers, not middleware.

R11-1: Handles PostgreSQL failures with graceful degradation.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from loguru import logger
from sqlalchemy.exc import (
    DatabaseError,
    InterfaceError,
    OperationalError,
)
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.utils.circuit_breaker import get_db_circuit_breaker
from bot.i18n.loader import get_translator
from bot.i18n.locales import DEFAULT_LANGUAGE


class DatabaseMiddleware(BaseMiddleware):
    """
    Database middleware - provides session factory to handlers.

    IMPORTANT: This middleware provides session_factory, NOT a live session.
    Each handler must manage its own session lifecycle to avoid long-running
    transactions during FSM states or async operations.
    """

    def __init__(self, session_pool: async_sessionmaker) -> None:
        """
        Initialize database middleware.

        Args:
            session_pool: SQLAlchemy async session maker
        """
        super().__init__()
        self.session_pool = session_pool

    def _determine_operation_type(
        self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]]
    ) -> str:
        """
        Determine operation type from handler name patterns.

        Args:
            handler: Handler callable

        Returns:
            Operation type: 'read', 'write', or 'admin'
        """
        handler_name = getattr(handler, "__name__", "")

        if any(pattern in handler_name.lower() for pattern in [
            "create", "update", "delete", "save", "store", "set", "add", "remove"
        ]):
            return "write"

        if "admin" in handler_name.lower():
            return "admin"

        return "read"

    async def _send_database_unavailable_message(self, event: TelegramObject) -> None:
        """
        Send database unavailable message to user.

        Args:
            event: Telegram event
        """
        if not isinstance(event, Message):
            return

        try:
            user_language = DEFAULT_LANGUAGE
            _ = get_translator(user_language)
            await event.answer(_("errors.database_unavailable"))
        except Exception as e:
            logger.error(f"Failed to send database_unavailable message: {e}")

    async def _send_database_error_message(
        self, event: TelegramObject, error: Exception, is_connection_failure: bool = False
    ) -> None:
        """
        Send appropriate database error message to user.

        Args:
            event: Telegram event
            error: Database error that occurred
            is_connection_failure: Whether this is a connection-level failure
        """
        if not isinstance(event, Message):
            return

        try:
            user_language = DEFAULT_LANGUAGE
            _ = get_translator(user_language)

            # R11-1: More specific error messages based on error type
            if isinstance(error, OperationalError):
                error_message = _("errors.database_operational_error")
            elif isinstance(error, InterfaceError):
                error_message = _("errors.database_interface_error")
            elif isinstance(error, DatabaseError):
                error_message = _("errors.database_general_error")
            else:
                error_message = (
                    _("errors.database_connection_failed")
                    if is_connection_failure
                    else _("errors.database_unavailable")
                )

            await event.answer(error_message)
        except Exception as msg_error:
            logger.warning(f"Failed to send error message to user: {msg_error}")

    async def _handle_handler_execution(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
        session: Any,
        circuit_breaker: Any,
    ) -> Any:
        """
        Execute handler and handle its success or failure.

        Args:
            handler: Handler callable
            event: Telegram event
            data: Handler data
            session: Database session
            circuit_breaker: Circuit breaker instance

        Returns:
            Handler result or None on database error
        """
        try:
            result = await handler(event, data)
            await session.commit()
            circuit_breaker.record_success()
            return result
        except (OperationalError, InterfaceError, DatabaseError) as e:
            await session.rollback()
            circuit_breaker.record_failure()
            logger.error(
                f"Database error in handler: {e}",
                extra={"error_type": type(e).__name__},
            )

            # FIXED: Don't try to create new DB session when DB is failing
            # R14-3: Error aggregation skipped when DB is unavailable
            await self._send_database_error_message(event, e)
            return None
        except Exception as e:
            await session.rollback()
            circuit_breaker.record_failure()
            logger.error(
                f"Unexpected error in handler: {e}",
                extra={"error_type": type(e).__name__},
            )
            raise

    async def _create_session_and_execute(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
        circuit_breaker: Any,
    ) -> Any:
        """
        Create database session and execute handler.

        Args:
            handler: Handler callable
            event: Telegram event
            data: Handler data
            circuit_breaker: Circuit breaker instance

        Returns:
            Handler result or None on error
        """
        try:
            async with self.session_pool() as session:
                data["session"] = session
                return await self._handle_handler_execution(
                    handler, event, data, session, circuit_breaker
                )
        except (OperationalError, InterfaceError, DatabaseError) as e:
            # R11-1: Database connection failure at middleware level
            circuit_breaker.record_failure()
            logger.critical(
                f"Database connection failure in middleware: {e}",
                extra={"error_type": type(e).__name__},
            )

            # FIXED: Don't try to create new DB session when DB is failing
            # R14-3: Error aggregation skipped when DB is unavailable
            await self._send_database_error_message(event, e, is_connection_failure=True)
            return None

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """
        Provide database session factory to handler.

        Handler is responsible for:
        1. Creating session via: async with session_factory() as session
        2. Managing transaction via: async with session.begin()
        3. Ensuring session is closed after use

        This approach prevents long-running transactions during FSM waits.

        Args:
            handler: Next handler
            event: Telegram event
            data: Handler data

        Returns:
            Handler result
        """
        # R11-1: Check circuit breaker before proceeding
        circuit_breaker = get_db_circuit_breaker()
        operation_type = self._determine_operation_type(handler)

        can_proceed, reason = circuit_breaker.can_proceed(operation_type)
        if not can_proceed:
            logger.warning(f"R11-1: Circuit breaker blocked operation: {reason}")
            await self._send_database_unavailable_message(event)
            return None

        # Provide session factory, not live session
        data["session_factory"] = self.session_pool

        # For backward compatibility, also provide session
        # NOTE: Keep until all handlers migrate to session_factory pattern
        return await self._create_session_and_execute(handler, event, data, circuit_breaker)
