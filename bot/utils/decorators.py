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
        # Extract event (Message or CallbackQuery) and data
        event = None
        data = kwargs

        # Find the event object in args
        for arg in args:
            if isinstance(arg, Message | CallbackQuery):
                event = arg
                break

        if not event:
            logger.error("require_admin: No Message or CallbackQuery found in args")
            return None

        # Check admin status from data
        is_admin = data.get("is_admin", False)

        if not is_admin:
            logger.warning(
                f"require_admin: Access denied for user "
                f"{event.from_user.id if event.from_user else 'unknown'}"
            )

            error_message = "❌ Эта функция доступна только администраторам"

            if isinstance(event, Message):
                await event.answer(error_message)
            elif isinstance(event, CallbackQuery):
                await event.answer(error_message, show_alert=True)

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
        # Extract event (Message or CallbackQuery) and data
        event = None
        data = kwargs

        # Find the event object in args
        for arg in args:
            if isinstance(arg, Message | CallbackQuery):
                event = arg
                break

        if not event:
            logger.error("require_super_admin: No Message or CallbackQuery found in args")
            return None

        # Check if user is admin first
        is_admin = data.get("is_admin", False)

        if not is_admin:
            logger.warning(
                f"require_super_admin: User {event.from_user.id if event.from_user else 'unknown'} "
                f"is not an admin"
            )

            error_message = "❌ Эта функция доступна только администраторам"

            if isinstance(event, Message):
                await event.answer(error_message)
            elif isinstance(event, CallbackQuery):
                await event.answer(error_message, show_alert=True)

            return None

        # Check super admin status
        # Try to get from data first (set by AdminAuthMiddleware)
        is_super_admin = data.get("is_super_admin", False)

        # Fallback: check Admin object
        if not is_super_admin:
            admin: Admin | None = data.get("admin")
            if admin:
                is_super_admin = admin.is_super_admin

        if not is_super_admin:
            logger.warning(
                f"require_super_admin: Access denied for admin user "
                f"{event.from_user.id if event.from_user else 'unknown'}"
            )

            error_message = "❌ Эта функция доступна только супер-администраторам"

            if isinstance(event, Message):
                await event.answer(error_message)
            elif isinstance(event, CallbackQuery):
                await event.answer(error_message, show_alert=True)

            return None

        # Super admin check passed, call handler
        return await handler(*args, **kwargs)

    return wrapper


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
        # Extract event (Message or CallbackQuery) and data
        event = None
        data = kwargs

        # Find the event object in args
        for arg in args:
            if isinstance(arg, Message | CallbackQuery):
                event = arg
                break

        if not event:
            logger.error("require_authenticated: No Message or CallbackQuery found in args")
            return None

        # Check if user exists in data
        user: User | None = data.get("user")

        if not user:
            logger.warning(
                f"require_authenticated: User not authenticated "
                f"(telegram_id={event.from_user.id if event.from_user else 'unknown'})"
            )

            error_message = (
                "❌ Вы не зарегистрированы в системе\n\n"
                "Пожалуйста, зарегистрируйтесь, используя команду /start"
            )

            if isinstance(event, Message):
                await event.answer(error_message)
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "❌ Требуется регистрация. Используйте /start",
                    show_alert=True
                )

            return None

        # Authentication check passed, call handler
        return await handler(*args, **kwargs)

    return wrapper


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
        # Extract event (Message or CallbackQuery)
        event = None

        # Find the event object in args
        for arg in args:
            if isinstance(arg, Message | CallbackQuery):
                event = arg
                break

        try:
            # Execute handler
            return await handler(*args, **kwargs)

        except IntegrityError as e:
            # Database integrity constraint violation
            logger.error(
                f"Database integrity error in {handler.__name__}: {e}",
                exc_info=True
            )

            error_message = (
                "❌ Ошибка целостности данных\n\n"
                "Возможно, запись уже существует или нарушены ограничения базы данных."
            )

            if event:
                if isinstance(event, Message):
                    await event.answer(error_message)
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        "❌ Ошибка целостности данных",
                        show_alert=True
                    )

            return None

        except OperationalError as e:
            # Database operational error (connection, etc.)
            logger.error(
                f"Database operational error in {handler.__name__}: {e}",
                exc_info=True
            )

            error_message = (
                "❌ Ошибка подключения к базе данных\n\n"
                "Пожалуйста, попробуйте позже."
            )

            if event:
                if isinstance(event, Message):
                    await event.answer(error_message)
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        "❌ Ошибка подключения к БД",
                        show_alert=True
                    )

            return None

        except DBAPIError as e:
            # Low-level database API error
            logger.error(
                f"Database API error in {handler.__name__}: {e}",
                exc_info=True
            )

            error_message = (
                "❌ Ошибка базы данных\n\n"
                "Пожалуйста, попробуйте позже."
            )

            if event:
                if isinstance(event, Message):
                    await event.answer(error_message)
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        "❌ Ошибка базы данных",
                        show_alert=True
                    )

            return None

        except SQLAlchemyError as e:
            # Generic SQLAlchemy error
            logger.error(
                f"SQLAlchemy error in {handler.__name__}: {e}",
                exc_info=True
            )

            error_message = (
                "❌ Ошибка при работе с базой данных\n\n"
                "Пожалуйста, попробуйте позже или обратитесь в поддержку."
            )

            if event:
                if isinstance(event, Message):
                    await event.answer(error_message)
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        "❌ Ошибка БД",
                        show_alert=True
                    )

            return None

        except Exception as e:
            # Catch any other unexpected errors
            logger.error(
                f"Unexpected error in {handler.__name__}: {e}",
                exc_info=True
            )

            error_message = (
                "❌ Произошла непредвиденная ошибка\n\n"
                "Администраторы уже уведомлены. Пожалуйста, попробуйте позже."
            )

            if event:
                if isinstance(event, Message):
                    await event.answer(error_message)
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        "❌ Непредвиденная ошибка",
                        show_alert=True
                    )

            return None

    return wrapper
