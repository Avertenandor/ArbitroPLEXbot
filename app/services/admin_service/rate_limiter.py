"""
Admin Service - Rate Limiter and Security.

This module handles:
- Failed login attempt tracking
- Automatic blocking for brute force attempts
- Security notifications
"""

from typing import Any

from aiogram.exceptions import TelegramAPIError
from loguru import logger
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.admin_repository import AdminRepository

from .constants import ADMIN_LOGIN_MAX_ATTEMPTS, ADMIN_LOGIN_WINDOW_SECONDS


class RateLimiter:
    """Handles rate limiting and security for admin logins."""

    def __init__(
        self,
        session: AsyncSession,
        admin_repo: AdminRepository,
        redis_client: Any | None = None,
    ) -> None:
        """
        Initialize rate limiter.

        Args:
            session: Database session
            admin_repo: Admin repository
            redis_client: Optional Redis client for rate limiting
        """
        self.session = session
        self.admin_repo = admin_repo
        self.redis_client = redis_client

    async def track_failed_login(self, telegram_id: int) -> None:
        """
        Track failed login attempt and block if limit exceeded.

        Args:
            telegram_id: Telegram user ID
        """
        if not self.redis_client:
            return  # No Redis, skip rate limiting

        try:
            key = f"admin_login_attempts:{telegram_id}"

            # Get current count
            count_str = await self.redis_client.get(key)
            count = int(count_str) if count_str else 0

            # Increment
            count += 1
            await self.redis_client.setex(
                key, ADMIN_LOGIN_WINDOW_SECONDS, str(count)
            )

            # Check if limit exceeded
            if count >= ADMIN_LOGIN_MAX_ATTEMPTS:
                from app.utils.security_logging import log_security_event

                log_security_event(
                    "Admin login rate limit exceeded",
                    {
                        "telegram_id": telegram_id,
                        "action_type": "ADMIN_LOGIN_BRUTE_FORCE",
                        "attempts": count,
                        "limit": ADMIN_LOGIN_MAX_ATTEMPTS,
                    }
                )

                # Block the Telegram ID
                await self._block_telegram_id(telegram_id)

        except (RedisError, ConnectionError, TimeoutError) as e:
            # R11-2: Redis failed, continue without rate limiting
            logger.warning(
                f"R11-2: Redis error tracking failed login for telegram_id={telegram_id}: {type(e).__name__}: {e}. "
                "Continuing without rate limiting (degraded mode).",
                exc_info=True
            )
        except ValueError as e:
            # Handle invalid count conversion
            logger.error(
                f"Invalid data in Redis for admin_login_attempts:{telegram_id}: {e}",
                exc_info=True
            )

    async def clear_failed_login_attempts(self, telegram_id: int) -> None:
        """
        Clear failed login attempts on successful login.

        Args:
            telegram_id: Telegram user ID
        """
        if not self.redis_client:
            return

        try:
            key = f"admin_login_attempts:{telegram_id}"
            await self.redis_client.delete(key)
        except (RedisError, ConnectionError, TimeoutError) as e:
            # R11-2: Redis failed, continue without clearing
            logger.warning(
                f"R11-2: Redis error clearing failed login attempts for telegram_id={telegram_id}: {type(e).__name__}: {e}. "
                "Continuing without clearing (degraded mode).",
                exc_info=True
            )

    async def _block_telegram_id(self, telegram_id: int) -> None:
        """
        Block Telegram ID after too many failed login attempts.

        Args:
            telegram_id: Telegram user ID to block
        """
        try:
            from app.models.blacklist import BlacklistActionType
            from app.services.blacklist_service import BlacklistService

            # Add to blacklist
            blacklist_service = BlacklistService(self.session)
            await blacklist_service.add_to_blacklist(
                telegram_id=telegram_id,
                reason="Too many failed admin login attempts",
                added_by_admin_id=None,  # System action
                action_type=BlacklistActionType.BLOCKED,
            )

            # If user exists, ban them
            from app.repositories.user_repository import UserRepository

            user_repo = UserRepository(self.session)
            user = await user_repo.get_by_telegram_id(telegram_id)
            if user:
                user.is_banned = True
                await self.session.flush()

            await self.session.commit()

            # Notify all super_admins
            await self._notify_super_admins_of_block(telegram_id)

            from app.utils.security_logging import log_security_event

            log_security_event(
                "Telegram ID blocked due to failed admin login attempts",
                {
                    "telegram_id": telegram_id,
                    "action_type": "AUTO_BLOCKED",
                    "reason": "Too many failed admin login attempts",
                }
            )

            # Send security notification
            from app.utils.admin_notifications import notify_security_event

            await notify_security_event(
                "Admin Login Brute Force Detected",
                f"Telegram ID {telegram_id} blocked after "
                f"{ADMIN_LOGIN_MAX_ATTEMPTS} failed login attempts",
                priority="critical",
            )

        except SQLAlchemyError as e:
            logger.error(
                f"Database error blocking telegram_id={telegram_id} for failed logins: {type(e).__name__}: {e}",
                exc_info=True
            )
            await self.session.rollback()
        except (ImportError, AttributeError) as e:
            logger.error(
                f"Module/attribute error while blocking telegram_id={telegram_id}: {type(e).__name__}: {e}",
                exc_info=True
            )
            await self.session.rollback()
        except TelegramAPIError as e:
            logger.error(
                f"Telegram API error while notifying about blocking telegram_id={telegram_id}: {type(e).__name__}: {e}",
                exc_info=True
            )

    async def _notify_super_admins_of_block(
        self, telegram_id: int
    ) -> None:
        """
        Notify all super_admins about automatic block.

        Args:
            telegram_id: Blocked Telegram ID
        """
        try:
            from aiogram import Bot

            from app.config.settings import settings

            # Get all super_admins
            super_admins = [
                a for a in await self.admin_repo.find_all()
                if a.is_super_admin
            ]

            if not super_admins:
                return

            # Create bot instance
            bot = Bot(token=settings.telegram_bot_token)

            try:
                notification_text = (
                    f"🚨 **Автоматическая блокировка**\n\n"
                    f"Telegram ID `{telegram_id}` был автоматически "
                    f"заблокирован из-за превышения лимита неуспешных "
                    f"попыток входа в админ-панель.\n\n"
                    f"Лимит: {ADMIN_LOGIN_MAX_ATTEMPTS} попыток за "
                    f"{ADMIN_LOGIN_WINDOW_SECONDS // 60} минут"
                )

                for super_admin in super_admins:
                    try:
                        await bot.send_message(
                            chat_id=super_admin.telegram_id,
                            text=notification_text,
                            parse_mode="Markdown",
                        )
                    except TelegramAPIError as e:
                        logger.error(
                            f"Telegram API error notifying super_admin {super_admin.id} "
                            f"(telegram_id={super_admin.telegram_id}): {type(e).__name__}: {e}",
                            exc_info=True
                        )
            finally:
                await bot.session.close()

        except SQLAlchemyError as e:
            logger.error(
                f"Database error fetching super_admins for notification: {type(e).__name__}: {e}",
                exc_info=True
            )
        except (ImportError, AttributeError) as e:
            logger.error(
                f"Module/attribute error initializing bot or settings: {type(e).__name__}: {e}",
                exc_info=True
            )
        except TelegramAPIError as e:
            logger.error(
                f"Telegram API error in super_admin notification: {type(e).__name__}: {e}",
                exc_info=True
            )
