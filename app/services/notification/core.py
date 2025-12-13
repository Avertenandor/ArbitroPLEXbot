"""
Core notification service.

Handles basic Telegram notification sending with multimedia support (PART5).
Includes Redis fallback queue support (R11-3) and bot-blocked user detection (R8-2).
"""

import asyncio
from typing import Any

from aiogram import Bot
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.constants import TELEGRAM_TIMEOUT
from app.models.failed_notification import FailedNotification
from app.repositories.failed_notification_repository import (
    FailedNotificationRepository,
)


class NotificationService:
    """
    Core notification service.

    Handles Telegram notifications with multimedia support (PART5).
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize notification service."""
        self.session = session
        self.failed_repo = FailedNotificationRepository(session)

    async def send_notification(
        self,
        bot: Bot,
        user_telegram_id: int,
        message: str,
        critical: bool = False,
        redis_client: Any | None = None,
    ) -> bool:
        """
        Send text notification.

        R11-3: If Redis is unavailable, writes to PostgreSQL fallback queue.

        Args:
            bot: Bot instance
            user_telegram_id: Telegram user ID
            message: Message text
            critical: Mark as critical
            redis_client: Optional Redis client for checking availability

        Returns:
            True if sent successfully or queued to fallback
        """
        # R11-3: Check if Redis is available
        redis_available = False
        if redis_client is not None:
            try:
                await redis_client.ping()
                redis_available = True
            except Exception:
                redis_available = False
                logger.warning(
                    "R11-3: Redis unavailable, will use PostgreSQL fallback"
                )

        # R11-3: If Redis is unavailable, write to PostgreSQL fallback
        if not redis_available:
            try:
                from app.models.notification_queue_fallback import (
                    NotificationQueueFallback,
                )
                from app.repositories.user_repository import UserRepository

                user_repo = UserRepository(self.session)
                user = await user_repo.get_by_telegram_id(user_telegram_id)

                if user:
                    # Create fallback queue entry
                    fallback_entry = NotificationQueueFallback(
                        user_id=user.id,
                        notification_type="text",
                        payload={
                            "message": message,
                            "critical": critical,
                        },
                        priority=100 if critical else 0,
                    )
                    self.session.add(fallback_entry)
                    await self.session.flush()

                    logger.info(
                        f"R11-3: Notification queued to PostgreSQL fallback "
                        f"for user {user_telegram_id} (user_id={user.id})"
                    )
                    return True
                else:
                    logger.warning(
                        f"R11-3: Cannot queue notification for unknown user "
                        f"{user_telegram_id}"
                    )
            except Exception as fallback_error:
                logger.error(
                    f"R11-3: Failed to write to PostgreSQL fallback: {fallback_error}",
                    exc_info=True,
                )

        try:
            await asyncio.wait_for(
                bot.send_message(
                    chat_id=user_telegram_id, text=message
                ),
                timeout=TELEGRAM_TIMEOUT,
            )

            # R8-2: If message sent successfully, check if user was previously blocked
            # and reset the flag (user unblocked the bot)
            try:
                from app.repositories.user_repository import UserRepository
                user_repo = UserRepository(self.session)
                user = await user_repo.get_by_telegram_id(user_telegram_id)
                if user and hasattr(user, 'bot_blocked') and user.bot_blocked:
                    # User unblocked the bot - reset flag
                    await user_repo.update(user.id, bot_blocked=False)
                    logger.info(
                        f"User {user_telegram_id} unblocked the bot, flag reset"
                    )
            except Exception as reset_error:
                # Don't fail notification if flag reset fails
                logger.warning(f"Failed to reset bot_blocked flag: {reset_error}")

            return True
        except Exception as e:
            # R8-2: Improved 403 error handling with specific TelegramAPIError check
            from datetime import UTC, datetime

            from aiogram.exceptions import TelegramAPIError

            # Check for specific "bot was blocked by the user" error
            is_bot_blocked = False
            if isinstance(e, TelegramAPIError):
                # Check error code and message
                if e.error_code == 403:
                    error_message = str(e).lower()
                    if "bot was blocked by the user" in error_message or "blocked" in error_message:
                        is_bot_blocked = True
            else:
                # Fallback for non-TelegramAPIError exceptions
                error_str = str(e).lower()
                if "403" in error_str or "forbidden" in error_str:
                    if "blocked" in error_str or "bot was blocked" in error_str:
                        is_bot_blocked = True

            if is_bot_blocked:
                logger.warning(
                    f"Bot blocked by user {user_telegram_id}",
                    extra={"user_id": user_telegram_id},
                )

                # Mark user as having blocked bot
                try:
                    from app.repositories.user_repository import UserRepository

                    user_repo = UserRepository(self.session)
                    user = await user_repo.get_by_telegram_id(user_telegram_id)
                    if user and not user.bot_blocked:
                        await user_repo.update(
                            user.id,
                            bot_blocked=True,
                            bot_blocked_at=datetime.now(UTC),
                        )
                        await self.session.commit()
                        logger.info(
                            f"Marked user {user_telegram_id} as bot_blocked"
                        )
                except Exception as update_error:
                    logger.error(
                        f"Failed to mark user as bot_blocked: {update_error}"
                    )

                # Don't save to failed notifications for blocked users
                # (they won't receive it anyway)
                return False

            logger.error(
                f"Failed to send notification: {e}",
                extra={"user_id": user_telegram_id},
            )

            # Save to failed notifications (PART5) for other errors
            await self._save_failed_notification(
                user_telegram_id,
                "text_message",
                message,
                str(e),
                critical,
            )
            return False

    async def send_photo(
        self,
        bot: Bot,
        user_telegram_id: int,
        file_id: str,
        caption: str | None = None,
    ) -> bool:
        """
        Send photo notification (PART5 multimedia).

        Args:
            bot: Bot instance
            user_telegram_id: Telegram user ID
            file_id: Telegram file ID
            caption: Photo caption

        Returns:
            True if sent successfully
        """
        try:
            await asyncio.wait_for(
                bot.send_photo(
                    chat_id=user_telegram_id,
                    photo=file_id,
                    caption=caption,
                ),
                timeout=TELEGRAM_TIMEOUT,
            )
            return True
        except TimeoutError:
            logger.warning(f"Timeout sending photo to {user_telegram_id}")
            await self._save_failed_notification(
                user_telegram_id,
                "photo",
                caption or "",
                "Timeout",
                metadata={"file_id": file_id},
            )
            return False
        except Exception as e:
            await self._save_failed_notification(
                user_telegram_id,
                "photo",
                caption or "",
                str(e),
                metadata={"file_id": file_id},
            )
            return False

    async def _save_failed_notification(
        self,
        user_telegram_id: int,
        notification_type: str,
        message: str,
        error: str,
        critical: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> FailedNotification:
        """Save failed notification for retry (PART5)."""
        return await self.failed_repo.create(
            user_telegram_id=user_telegram_id,
            notification_type=notification_type,
            message=message,
            last_error=error,
            critical=critical,
            notification_metadata=metadata,
        )

    async def notify_user(
        self,
        user_id: int,
        message: str,
        critical: bool = False,
    ) -> bool:
        """
        Notify user by database ID (wrapper for send_notification).

        Args:
            user_id: Database User ID
            message: Message text
            critical: Mark as critical

        Returns:
            True if sent
        """
        try:
            from app.repositories.user_repository import UserRepository
            user_repo = UserRepository(self.session)
            user = await user_repo.get_by_id(user_id)

            if not user or not user.telegram_id:
                logger.warning(f"Cannot notify user {user_id}: User not found or no telegram_id")
                return False

            from aiogram import Bot
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode

            from app.config.settings import settings
            from app.services.bot_provider import get_bot

            bot = get_bot()
            should_close = False

            if not bot:
                try:
                    bot = Bot(
                        token=settings.telegram_bot_token,
                        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
                    )
                    should_close = True
                except Exception as e:
                    logger.error(f"Failed to create fallback bot instance: {e}")
                    return False

            try:
                return await self.send_notification(
                    bot, user.telegram_id, message, critical
                )
            finally:
                if should_close and bot:
                    await bot.session.close()

        except Exception as e:
            logger.error(f"Error in notify_user: {e}", exc_info=True)
            return False
