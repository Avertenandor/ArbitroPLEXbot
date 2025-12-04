"""
Common decorators for Telegram bot handlers.

Provides reusable decorators for authentication, authorization, and error handling.
"""

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, TypeVar

from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.exc import (
    DBAPIError,
    IntegrityError,
    OperationalError,
    SQLAlchemyError,
)

from app.models.admin import Admin
from app.models.user import User

# Type variable for handler return type
T = TypeVar("T")


# Helper functions for decorator logic


def _extract_event(args: tuple[Any, ...]) -> Message | CallbackQuery | None:
    """Extract Message or CallbackQuery event from handler args."""
    for arg in args:
        if isinstance(arg, (Message, CallbackQuery)):
            return arg
    return None


async def _send_error_message(
    event: Message | CallbackQuery,
    full_message: str,
    alert_message: str
) -> None:
    """Send error message to user via Message or CallbackQuery."""
    if isinstance(event, Message):
        await event.answer(full_message)
    elif isinstance(event, CallbackQuery):
        await event.answer(alert_message, show_alert=True)


def require_admin(
    handler: Callable[..., Awaitable[T]]
) -> Callable[..., Awaitable[T | None]]:
    """
    Decorator to require admin privileges for handler.

    Checks if user has admin privileges via AdminRepository.
    Blocks access if user is not an admin.

    Usage:
        @router.message(F.text == "Admin Panel")
        @require_admin
        async def admin_panel(message: Message, **data: Any) -> None:
            # Handler code here
            pass

    Args:
        handler: The handler function to decorate

    Returns:
        Wrapped handler that checks admin status
    """

    @wraps(handler)
    async def wrapper(*args: Any, **kwargs: Any) -> T | None:
        event = _extract_event(args)
        if not event:
            logger.error("require_admin: No Message or CallbackQuery found in args")
            return None

        # Check admin status from data
        is_admin = kwargs.get("is_admin", False)
        if not is_admin:
            user_id = event.from_user.id if event.from_user else "unknown"
            logger.warning(f"require_admin: Access denied for user {user_id}")

            error_message = "❌ Эта функция доступна только администраторам"
            await _send_error_message(event, error_message, error_message)
            return None

        # Admin check passed, call handler
        return await handler(*args, **kwargs)

    return wrapper


def require_super_admin(
    handler: Callable[..., Awaitable[T]]
) -> Callable[..., Awaitable[T | None]]:
    """
    Decorator to require super admin privileges for handler.

    Checks if user is a super admin via is_super_admin flag or Admin model.
    Blocks access if user is not a super admin.

    Usage:
        @router.message(F.text == "Super Admin Panel")
        @require_super_admin
        async def super_admin_panel(message: Message, **data: Any) -> None:
            # Handler code here
            pass

    Args:
        handler: The handler function to decorate

    Returns:
        Wrapped handler that checks super admin status
    """

    @wraps(handler)
    async def wrapper(*args: Any, **kwargs: Any) -> T | None:
        event = _extract_event(args)
        if not event:
            logger.error("require_super_admin: No Message or CallbackQuery found in args")
            return None

        user_id = event.from_user.id if event.from_user else "unknown"

        # Check if user is admin first
        is_admin = kwargs.get("is_admin", False)
        if not is_admin:
            logger.warning(f"require_super_admin: User {user_id} is not an admin")
            error_message = "❌ Эта функция доступна только администраторам"
            await _send_error_message(event, error_message, error_message)
            return None

        # Check super admin status (from data or Admin object)
        is_super_admin = _check_super_admin_status(kwargs)
        if not is_super_admin:
            logger.warning(f"require_super_admin: Access denied for admin user {user_id}")
            error_message = "❌ Эта функция доступна только супер-администраторам"
            await _send_error_message(event, error_message, error_message)
            return None

        # Super admin check passed, call handler
        return await handler(*args, **kwargs)

    return wrapper


def _check_super_admin_status(data: dict[str, Any]) -> bool:
    """Check if user has super admin status from data or Admin object."""
    # Try to get from data first (set by AdminAuthMiddleware)
    is_super_admin = data.get("is_super_admin", False)
    if is_super_admin:
        return True

    # Fallback: check Admin object
    admin: Admin | None = data.get("admin")
    if admin:
        return admin.is_super_admin

    return False


def require_authenticated(
    handler: Callable[..., Awaitable[T]]
) -> Callable[..., Awaitable[T | None]]:
    """
    Decorator to require user authentication for handler.

    Checks if user is registered and authenticated via User model.
    Blocks access if user is not authenticated.

    Usage:
        @router.message(F.text == "My Profile")
        @require_authenticated
        async def my_profile(message: Message, **data: Any) -> None:
            # Handler code here
            pass

    Args:
        handler: The handler function to decorate

    Returns:
        Wrapped handler that checks authentication status
    """

    @wraps(handler)
    async def wrapper(*args: Any, **kwargs: Any) -> T | None:
        event = _extract_event(args)
        if not event:
            logger.error("require_authenticated: No Message or CallbackQuery found in args")
            return None

        # Check if user exists in data
        user: User | None = kwargs.get("user")
        if not user:
            user_id = event.from_user.id if event.from_user else "unknown"
            logger.warning(f"require_authenticated: User not authenticated (telegram_id={user_id})")

            full_message = (
                "❌ Вы не зарегистрированы в системе\n\n"
                "Пожалуйста, зарегистрируйтесь, используя команду /start"
            )
            alert_message = "❌ Требуется регистрация. Используйте /start"
            await _send_error_message(event, full_message, alert_message)
            return None

        # Authentication check passed, call handler
        return await handler(*args, **kwargs)

    return wrapper


# Error configuration for database error handling
_DB_ERROR_CONFIG = {
    IntegrityError: {
        "log_prefix": "Database integrity error",
        "full_message": (
            "❌ Ошибка целостности данных\n\n"
            "Возможно, запись уже существует или нарушены ограничения базы данных."
        ),
        "alert_message": "❌ Ошибка целостности данных",
    },
    OperationalError: {
        "log_prefix": "Database operational error",
        "full_message": (
            "❌ Ошибка подключения к базе данных\n\n"
            "Пожалуйста, попробуйте позже."
        ),
        "alert_message": "❌ Ошибка подключения к БД",
    },
    DBAPIError: {
        "log_prefix": "Database API error",
        "full_message": (
            "❌ Ошибка базы данных\n\n"
            "Пожалуйста, попробуйте позже."
        ),
        "alert_message": "❌ Ошибка базы данных",
    },
    SQLAlchemyError: {
        "log_prefix": "SQLAlchemy error",
        "full_message": (
            "❌ Ошибка при работе с базой данных\n\n"
            "Пожалуйста, попробуйте позже или обратитесь в поддержку."
        ),
        "alert_message": "❌ Ошибка БД",
    },
}


async def _handle_db_exception(
    exception: Exception,
    handler_name: str,
    event: Message | CallbackQuery | None
) -> None:
    """Handle database exception by logging and sending user message."""
    # Get error config or use generic error
    error_config = _DB_ERROR_CONFIG.get(type(exception))

    if error_config:
        log_prefix = error_config["log_prefix"]
        full_message = error_config["full_message"]
        alert_message = error_config["alert_message"]
    else:
        # Generic error for unexpected exceptions
        log_prefix = "Unexpected error"
        full_message = (
            "❌ Произошла непредвиденная ошибка\n\n"
            "Администраторы уже уведомлены. Пожалуйста, попробуйте позже."
        )
        alert_message = "❌ Непредвиденная ошибка"

    # Log the error
    logger.error(f"{log_prefix} in {handler_name}: {exception}", exc_info=True)

    # Send user message if event exists
    if event:
        await _send_error_message(event, full_message, alert_message)


def handle_db_errors(
    handler: Callable[..., Awaitable[T]]
) -> Callable[..., Awaitable[T | None]]:
    """
    Decorator to handle database errors in handlers.

    Wraps handler with try/except to catch SQLAlchemy database errors.
    Logs errors and sends user-friendly error messages.

    Usage:
        @router.message(F.text == "Create Deposit")
        @handle_db_errors
        async def create_deposit(message: Message, **data: Any) -> None:
            # Handler code that may cause DB errors
            pass

    Args:
        handler: The handler function to decorate

    Returns:
        Wrapped handler with database error handling
    """

    @wraps(handler)
    async def wrapper(*args: Any, **kwargs: Any) -> T | None:
        event = _extract_event(args)

        try:
            return await handler(*args, **kwargs)
        except (IntegrityError, OperationalError, DBAPIError, SQLAlchemyError, Exception) as e:
            await _handle_db_exception(e, handler.__name__, event)
            return None

    return wrapper
