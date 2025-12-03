"""
Session middleware.

Handles Pay-to-Use authorization, session timeouts, and PLEX balance checks.
"""

from datetime import UTC, datetime
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from aiogram.fsm.context import FSMContext
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings

SESSION_TTL = 1500  # 25 minutes
SESSION_KEY_PREFIX = "auth_session:"
PLEX_CHECK_INTERVAL = 3600  # 1 hour between PLEX balance checks
PLEX_CHECK_KEY_PREFIX = "plex_check:"


class SessionMiddleware(BaseMiddleware):
    """
    Middleware for session management.
    
    Responsibilities:
    - Check Pay-to-Use session validity
    - Periodically verify PLEX balance (every hour)
    - Send warnings for insufficient PLEX
    """

    def __init__(self, redis: Redis) -> None:
        """Initialize middleware with Redis client."""
        self.redis = redis

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Process update through middleware."""
        # Get Telegram user
        tg_user = data.get("event_from_user")
        if not tg_user:
            logger.debug("SessionMiddleware: no tg_user, passing through")
            return await handler(event, data)

        user_id = tg_user.id
        logger.debug(f"SessionMiddleware: user_id={user_id}")

        # Allow specific commands/callbacks always
        if isinstance(event, Message) and event.text:
            logger.debug(f"SessionMiddleware: message text={event.text!r}")
            if event.text.startswith("/start"):
                logger.info(f"SessionMiddleware: /start detected, passing through for user {user_id}")
                return await handler(event, data)

        if isinstance(event, CallbackQuery) and event.data:
            if event.data in ("check_payment", "start_after_auth"):
                return await handler(event, data)

        # Check session
        session_key = f"{SESSION_KEY_PREFIX}{user_id}"
        has_session = await self.redis.exists(session_key)

        if not has_session:
            # Session expired
            await self._handle_session_expired(event, data)
            return None

        # Update session TTL (sliding window)
        await self.redis.expire(session_key, SESSION_TTL)

        # Check PLEX balance periodically (for users with deposits)
        db_user = data.get("user")
        if db_user:
            await self._check_plex_balance_if_needed(
                event, data, db_user, user_id
            )

        return await handler(event, data)

    async def _handle_session_expired(
        self,
        event: TelegramObject,
        data: dict[str, Any],
    ) -> None:
        """Handle expired session."""
        if not isinstance(event, (Message, CallbackQuery)):
            return

        # Reset FSM
        state: FSMContext | None = data.get("state")
        if state:
            await state.clear()

        msg_text = (
            "⏳ **Сессия истекла**\n\n"
            "Для продолжения работы необходимо оплатить доступ.\n"
            "Пожалуйста, введите /start для начала."
        )

        try:
            if isinstance(event, Message):
                await event.answer(msg_text, parse_mode="Markdown")
            elif isinstance(event, CallbackQuery):
                if event.message:
                    await event.message.answer(msg_text, parse_mode="Markdown")
                await event.answer()
        except Exception as e:
            logger.warning(f"Failed to send session expiration message: {e}")

    async def _check_plex_balance_if_needed(
        self,
        event: TelegramObject,
        data: dict[str, Any],
        db_user: Any,
        user_id: int,
    ) -> None:
        """
        Check PLEX balance if check interval passed.
        
        Only checks once per hour to avoid excessive blockchain calls.
        """
        # Check if we need to verify PLEX balance
        plex_check_key = f"{PLEX_CHECK_KEY_PREFIX}{user_id}"
        last_check = await self.redis.get(plex_check_key)
        
        if last_check:
            # Already checked recently
            return
        
        # Mark as checked (set TTL for interval)
        await self.redis.setex(plex_check_key, PLEX_CHECK_INTERVAL, "1")
        
        try:
            # Get DB session from data
            session: AsyncSession | None = data.get("session")
            if not session:
                return
            
            # Import here to avoid circular imports
            from app.services.plex_payment_service import PlexPaymentService
            
            plex_service = PlexPaymentService(session)
            
            # Get warning message if PLEX is insufficient
            warning = await plex_service.get_insufficient_plex_message(db_user.id)
            
            if warning:
                # Send warning
                try:
                    if isinstance(event, Message):
                        await event.answer(
                            warning,
                            parse_mode="Markdown",
                        )
                    elif isinstance(event, CallbackQuery) and event.message:
                        await event.message.answer(
                            warning,
                            parse_mode="Markdown",
                        )
                except Exception as e:
                    logger.warning(f"Failed to send PLEX warning: {e}")
                
                logger.warning(
                    f"Insufficient PLEX balance for user {user_id}"
                )
                
        except Exception as e:
            logger.error(f"PLEX balance check failed for user {user_id}: {e}")

