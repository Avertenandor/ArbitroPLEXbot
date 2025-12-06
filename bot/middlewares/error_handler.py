"""
Global Error Handler Middleware.

Catches unhandled exceptions and notifies admins.
Sends friendly message to users - never shows technical details.
"""

import traceback
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, Message, TelegramObject, Update, User
from loguru import logger

from app.config.settings import settings


class ErrorHandlerMiddleware(BaseMiddleware):
    """
    Global error handler middleware.

    - Logs all exceptions
    - Notifies admins with technical details
    - Sends friendly message to user (no technical info!)
    """

    def _get_user(self, event: TelegramObject) -> User | None:
        """Extract user from event."""
        if isinstance(event, Update):
            if event.message:
                return event.message.from_user
            if event.callback_query:
                return event.callback_query.from_user
            if event.inline_query:
                return event.inline_query.from_user
            if event.my_chat_member:
                return event.my_chat_member.from_user
            if event.chat_member:
                return event.chat_member.from_user
        elif isinstance(event, Message):
            return event.from_user
        elif isinstance(event, CallbackQuery):
            return event.from_user
        return None

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Execute middleware."""
        try:
            return await handler(event, data)
        except Exception as e:
            # Log error
            logger.exception(f"Unhandled exception: {e}")

            bot: Bot | None = data.get("bot")
            user = self._get_user(event)

            # 1. Send friendly message to user (NO technical details!)
            if bot and user:
                try:
                    await bot.send_message(
                        chat_id=user.id,
                        text=(
                            "❌ Произошла временная ошибка.\n\n"
                            "Администраторы уже уведомлены и работают над решением.\n"
                            "Пожалуйста, попробуйте позже или обратитесь в поддержку."
                        ),
                    )
                except Exception as user_notify_error:
                    logger.warning(f"Failed to notify user: {user_notify_error}")

            # 2. Notify admins with technical details
            admin_ids = settings.get_admin_ids()
            if bot and admin_ids:
                try:
                    error_trace = traceback.format_exc()[-800:]  # Last 800 chars
                    # Escape special characters for HTML
                    error_trace_escaped = (
                        error_trace
                        .replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;")
                    )

                    # Get user info for context
                    user_info = "Unknown"
                    if user:
                        user_info = (
                            f"@{user.username}"
                            if user.username
                            else f"ID: {user.id}"
                        )

                    error_msg = str(e)[:200].replace("<", "&lt;").replace(">", "&gt;")
                    text = (
                        f"🚨 <b>CRITICAL ERROR</b>\n\n"
                        f"👤 User: {user_info}\n"
                        f"❌ Exception: <code>{type(e).__name__}</code>\n"
                        f"📝 Message: <code>{error_msg}</code>\n\n"
                        f"<pre>{error_trace_escaped}</pre>"
                    )
                    # Notify first admin only (to avoid spam)
                    await bot.send_message(
                        chat_id=admin_ids[0],
                        text=text[:4096],
                        parse_mode="HTML",
                    )
                except Exception as notify_error:
                    logger.error(f"Failed to notify admin: {notify_error}")

            # Return None to prevent crash
            return None
