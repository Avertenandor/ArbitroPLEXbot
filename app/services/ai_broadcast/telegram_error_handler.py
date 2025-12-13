"""Telegram error handling utilities for AI Broadcast Service."""

from typing import Any, Callable, TypeVar, ParamSpec
from functools import wraps

from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from loguru import logger


P = ParamSpec("P")
R = TypeVar("R")


class TelegramErrorHandler:
    """Handles Telegram API errors with consistent logging."""

    @staticmethod
    def handle_send_error(
        error: Exception,
        user_identifier: str | int,
        context: str = "sending message",
    ) -> dict[str, Any]:
        """
        Handle Telegram API error and return error dict.

        Args:
            error: The exception that occurred
            user_identifier: User identifier for logging
            context: Context of the operation

        Returns:
            Error result dictionary
        """
        if isinstance(error, TelegramForbiddenError):
            logger.warning(
                f"User {user_identifier} blocked the bot or "
                f"bot lacks permission ({context})"
            )
            return {
                "success": False,
                "error": "Пользователь заблокировал бота",
            }

        if isinstance(error, TelegramBadRequest):
            logger.error(
                f"Invalid request when {context} to "
                f"{user_identifier}: {error}"
            )
            return {
                "success": False,
                "error": (
                    "Ошибка отправки сообщения "
                    "(неверный запрос)"
                ),
            }

        if isinstance(error, TelegramRetryAfter):
            logger.warning(
                f"Rate limit hit when {context} to "
                f"{user_identifier}, "
                f"retry after {error.retry_after}s"
            )
            return {
                "success": False,
                "error": (
                    "Превышен лимит запросов, повторите позже"
                ),
            }

        if isinstance(error, TelegramAPIError):
            logger.error(
                f"Telegram API error when {context} to "
                f"{user_identifier}: "
                f"{error}"
            )
            return {
                "success": False,
                "error": "Ошибка Telegram API",
            }

        logger.error(
            f"Unexpected error {context} to {user_identifier}: {error}",
            exc_info=True,
        )
        return {
            "success": False,
            "error": "Ошибка отправки сообщения",
        }

    @staticmethod
    def handle_broadcast_error(
        error: Exception,
        group: str,
        context: str = "broadcast",
    ) -> dict[str, Any]:
        """
        Handle error during broadcast operation.

        Args:
            error: The exception that occurred
            group: Target group name
            context: Context of the operation

        Returns:
            Error result dictionary
        """
        if isinstance(error, TelegramAPIError):
            logger.error(
                f"Telegram API error during {context} to '{group}': "
                f"{error}"
            )
            return {
                "success": False,
                "error": f"Ошибка Telegram API: {str(error)}",
            }

        logger.error(
            f"Unexpected error during {context} to '{group}': {error}",
            exc_info=True,
        )
        return {
            "success": False,
            "error": str(error),
        }

    @staticmethod
    async def send_with_error_handling(
        send_func: Callable[P, R],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> tuple[bool, Exception | None]:
        """
        Execute send function with error handling.

        Args:
            send_func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Tuple of (success: bool, error: Exception | None)
        """
        try:
            await send_func(*args, **kwargs)
            return True, None
        except (
            TelegramForbiddenError,
            TelegramBadRequest,
            TelegramAPIError,
        ) as e:
            return False, e
        except Exception as e:
            logger.error(
                f"Unexpected error in send operation: {e}",
                exc_info=True,
            )
            return False, e

    @staticmethod
    def log_send_result(
        success: bool,
        error: Exception | None,
        user_id: int,
        context: str = "message",
    ) -> None:
        """
        Log the result of a send operation.

        Args:
            success: Whether the send was successful
            error: The error if send failed
            user_id: User telegram ID
            context: Description of what was sent
        """
        if success:
            logger.debug(f"Successfully sent {context} to user {user_id}")
        elif isinstance(error, TelegramForbiddenError):
            logger.debug(f"User {user_id} blocked the bot")
        elif isinstance(error, (TelegramBadRequest, TelegramAPIError)):
            logger.warning(f"Failed to send {context} to {user_id}: {error}")
        else:
            logger.error(
                f"Unexpected error sending {context} to {user_id}: {error}"
            )
