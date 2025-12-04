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
from bot.i18n.loader import get_translator, get_user_language
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
        
        # Determine operation type (read/write/admin)
        # Try to determine from handler name or event type
        operation_type = "read"  # Default to read
        
        # Detect write operations from handler name patterns
        handler_name = getattr(handler, "__name__", "")
        if any(pattern in handler_name.lower() for pattern in [
            "create", "update", "delete", "save", "store", "set", "add", "remove"
        ]):
            operation_type = "write"
        elif "admin" in handler_name.lower():
            operation_type = "admin"
        
        can_proceed, reason = circuit_breaker.can_proceed(operation_type)
        if not can_proceed:
            logger.warning(f"R11-1: Circuit breaker blocked operation: {reason}")
            if isinstance(event, Message):
                try:
                    # FIXED: Don't try to access DB when circuit breaker is open
                    # Use default language instead to avoid connection leak
                    user_language = DEFAULT_LANGUAGE
                    _ = get_translator(user_language)
                    await event.answer(_("errors.database_unavailable"))
                except Exception as e:
                    logger.error(f"Failed to send database_unavailable message: {e}")
                    pass
            return None
        
        # Provide session factory, not live session
        data["session_factory"] = self.session_pool
        
        # For backward compatibility, also provide session
        # NOTE: Keep until all handlers migrate to session_factory pattern
        try:
            async with self.session_pool() as session:
                data["session"] = session
                try:
                    result = await handler(event, data)
                    await session.commit()
                    # R11-1: Record success
                    circuit_breaker.record_success()
                    return result
                except (OperationalError, InterfaceError, DatabaseError) as e:
                    # R11-1: Handle database failures gracefully
                    await session.rollback()
                    # R11-1: Record failure in circuit breaker
                    circuit_breaker.record_failure()
                    logger.error(
                        f"Database error in handler: {e}",
                        extra={"error_type": type(e).__name__},
                    )

                    # FIXED: Don't try to create new DB session when DB is failing
                    # This would cause connection leak. Just log to file instead.
                    # R14-3: Error aggregation skipped when DB is unavailable
                    
                    # Send graceful error message to user if it's a Message event
                    if isinstance(event, Message):
                        try:
                            # FIXED: Don't try to access DB when DB is failing
                            # Use default language to avoid connection leak
                            user_language = DEFAULT_LANGUAGE
                            
                            _ = get_translator(user_language)
                            
                            # R11-1: More specific error messages based on error type
                            if isinstance(e, OperationalError):
                                error_message = _("errors.database_operational_error")
                            elif isinstance(e, InterfaceError):
                                error_message = _("errors.database_interface_error")
                            elif isinstance(e, DatabaseError):
                                error_message = _("errors.database_general_error")
                            else:
                                error_message = _("errors.database_unavailable")
                            
                            await event.answer(error_message)
                        except Exception as msg_error:
                            # If we can't send message, log and continue
                            logger.warning(
                                f"Failed to send error message to user: {msg_error}"
                            )
                    
                    # Don't re-raise - graceful degradation
                    return None
                except Exception as e:
                    await session.rollback()
                    # R11-1: Record non-database exceptions as failures too
                    circuit_breaker.record_failure()
                    logger.error(
                        f"Unexpected error in handler: {e}",
                        extra={"error_type": type(e).__name__},
                    )
                    raise
        except (OperationalError, InterfaceError, DatabaseError) as e:
            # R11-1: Database connection failure at middleware level
            # R11-1: Record failure in circuit breaker
            circuit_breaker.record_failure()
            logger.critical(
                f"Database connection failure in middleware: {e}",
                extra={"error_type": type(e).__name__},
            )

            # FIXED: Don't try to create new DB session when DB is failing
            # This would cause connection leak. Just log to file instead.
            # R14-3: Error aggregation skipped when DB is unavailable
            
            # Send graceful error message to user if it's a Message event
            if isinstance(event, Message):
                try:
                    # FIXED: Don't try to access DB when DB connection failed
                    # Use default language to avoid connection leak
                    user_language = DEFAULT_LANGUAGE
                    
                    _ = get_translator(user_language)
                    
                    # R11-1: More specific error messages based on error type
                    if isinstance(e, OperationalError):
                        error_message = _("errors.database_operational_error")
                    elif isinstance(e, InterfaceError):
                        error_message = _("errors.database_interface_error")
                    elif isinstance(e, DatabaseError):
                        error_message = _("errors.database_general_error")
                    else:
                        error_message = _("errors.database_connection_failed")
                    
                    await event.answer(error_message)
                except Exception as msg_error:
                    logger.warning(
                        f"Failed to send error message to user: {msg_error}"
                    )
            
            # Don't re-raise - graceful degradation
            return None
