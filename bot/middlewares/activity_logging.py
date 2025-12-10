"""
User Activity Logging Middleware.

Automatically logs all user interactions with the bot.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_activity import ActivityType
from app.services.user_activity_service import UserActivityService


class ActivityLoggingMiddleware(BaseMiddleware):
    """
    Middleware that logs all user interactions.

    Logs:
    - All messages
    - All button clicks (callbacks)
    - Special events (start, menu, etc.)
    """

    # Commands that trigger specific activity types
    SPECIAL_COMMANDS = {
        "/start": ActivityType.START,
        "🚀 Начать": ActivityType.START,
    }

    # Menu buttons to track
    MENU_BUTTONS = {
        "⬅️ Главное меню": ActivityType.MENU_OPEN,
        "📊 Баланс": ActivityType.BALANCE_VIEW,
        "👤 Мой профиль": ActivityType.PROFILE_VIEW,
        "👥 Рефералы": ActivityType.REFERRAL_LINK_VIEW,
        "🔗 Моя ссылка": ActivityType.REFERRAL_LINK_SHARED,
        "📞 Поддержка": ActivityType.SUPPORT_REQUEST,
    }

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Process event and log activity."""
        # Get session and user info
        session: AsyncSession | None = data.get("session")
        user: User | None = data.get("user")

        # Extract event details
        telegram_id: int | None = None
        message_text: str | None = None
        is_callback = False

        if isinstance(event, Update):
            if event.message:
                telegram_id = (
                    event.message.from_user.id
                    if event.message.from_user else None
                )
                message_text = event.message.text
            elif event.callback_query:
                telegram_id = (
                    event.callback_query.from_user.id
                    if event.callback_query.from_user else None
                )
                message_text = event.callback_query.data
                is_callback = True
        elif isinstance(event, Message):
            telegram_id = event.from_user.id if event.from_user else None
            message_text = event.text
        elif isinstance(event, CallbackQuery):
            telegram_id = event.from_user.id if event.from_user else None
            message_text = event.data
            is_callback = True

        # Log activity if we have session and telegram_id
        if session and telegram_id:
            try:
                await self._log_activity(
                    session=session,
                    telegram_id=telegram_id,
                    user_id=user.id if user else None,
                    message_text=message_text,
                    is_callback=is_callback,
                )
            except Exception as e:
                # Don't fail the handler if logging fails
                logger.warning(f"Activity logging failed: {e}")

        # Continue to handler
        return await handler(event, data)

    async def _log_activity(
        self,
        session: AsyncSession,
        telegram_id: int,
        user_id: int | None,
        message_text: str | None,
        is_callback: bool,
    ) -> None:
        """Log the activity."""
        activity_service = UserActivityService(session)

        # Determine activity type
        activity_type = ActivityType.BUTTON_CLICKED if is_callback else ActivityType.MESSAGE_SENT

        # Check for special commands/buttons
        if message_text:
            if message_text in self.SPECIAL_COMMANDS:
                activity_type = self.SPECIAL_COMMANDS[message_text]
            elif message_text in self.MENU_BUTTONS:
                activity_type = self.MENU_BUTTONS[message_text]
            elif message_text.startswith("/start ref_"):
                activity_type = ActivityType.START_REFERRAL

        # Log the activity
        await activity_service.log(
            telegram_id=telegram_id,
            activity_type=activity_type,
            user_id=user_id,
            message_text=message_text,
            description=self._get_description(activity_type, message_text),
        )

        # Commit is handled by session middleware
        await session.commit()

    def _get_description(
        self,
        activity_type: str,
        message_text: str | None,
    ) -> str:
        """Generate human-readable description."""
        if activity_type == ActivityType.START:
            return "Нажал /start"
        elif activity_type == ActivityType.START_REFERRAL:
            return "Пришёл по реферальной ссылке"
        elif activity_type == ActivityType.MENU_OPEN:
            return "Открыл главное меню"
        elif activity_type == ActivityType.BALANCE_VIEW:
            return "Посмотрел баланс"
        elif activity_type == ActivityType.PROFILE_VIEW:
            return "Открыл профиль"
        elif activity_type == ActivityType.REFERRAL_LINK_VIEW:
            return "Открыл рефералов"
        elif activity_type == ActivityType.SUPPORT_REQUEST:
            return "Открыл поддержку"
        elif message_text:
            preview = message_text[:50] + "..." if len(message_text) > 50 else message_text
            return f"{'Кнопка' if activity_type == ActivityType.BUTTON_CLICKED else 'Сообщение'}: {preview}"
        return "Действие"
