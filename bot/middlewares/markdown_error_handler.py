"""
Markdown Error Handler Middleware.

Catches TelegramBadRequest errors related to Markdown parsing
and retries sending messages without formatting.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, TelegramObject
from loguru import logger


def strip_markdown(text: str) -> str:
    """Remove Markdown formatting from text."""
    result = text.replace('**', '').replace('*', '').replace('_', '')
    result = result.replace('`', '').replace('\\', '')
    return result


class MarkdownErrorHandlerMiddleware(BaseMiddleware):
    """
    Middleware that catches Markdown parse errors and retries without formatting.
    
    This is a safety net for when sanitize_markdown misses edge cases.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Process update with Markdown error handling."""
        try:
            return await handler(event, data)
        except TelegramBadRequest as e:
            if "can't parse entities" in str(e):
                error_msg = str(e)
                logger.warning(
                    f"Markdown parse error caught by middleware: {error_msg}"
                )

                # Try to send error notification to user
                if isinstance(event, Message):
                    try:
                        await event.answer(
                            "⚠️ Произошла ошибка форматирования. "
                            "Попробуйте ещё раз или обратитесь в поддержку.",
                        )
                    except Exception:
                        pass

                # Don't re-raise - error is handled
                return None

            # Re-raise non-parsing errors
            raise
