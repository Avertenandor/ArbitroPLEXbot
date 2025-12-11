"""
Session middleware.

Handles Pay-to-Use authorization, session timeouts, and PLEX balance checks.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, TelegramObject, Update
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession


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

    Note: This middleware is registered on dp.update, so it receives
    Update objects, not Message/CallbackQuery directly.
    """

    def __init__(self, redis: Redis) -> None:
        """Initialize middleware with Redis client."""
        self.redis = redis

    def _extract_event(self, event: TelegramObject) -> Message | CallbackQuery | None:
        """
        Extract Message or CallbackQuery from Update object.

        If event is already Message/CallbackQuery, return as-is.
        If event is Update, extract the inner message or callback.
        """
        if isinstance(event, Message):
            return event
        if isinstance(event, CallbackQuery):
            return event
        if isinstance(event, Update):
            if event.message:
                return event.message
            if event.callback_query:
                return event.callback_query
            # Handle edited messages too
            if event.edited_message:
                return event.edited_message
        return None

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Process update through middleware."""
        # Extract actual event (Message or CallbackQuery) from Update
        actual_event = self._extract_event(event)

        logger.debug(
            f"SessionMiddleware: event type={type(event).__name__}, "
            f"actual_event type={type(actual_event).__name__ if actual_event else 'None'}"
        )

        # Get Telegram user
        tg_user = data.get("event_from_user")
        if not tg_user:
            logger.debug("SessionMiddleware: no tg_user, passing through")
            return await handler(event, data)

        user_id = tg_user.id
        logger.debug(f"SessionMiddleware: user_id={user_id}")

        # Allow /start command always
        if isinstance(actual_event, Message) and actual_event.text:
            logger.debug(f"SessionMiddleware: message text={actual_event.text!r}")
            if actual_event.text.startswith("/start"):
                logger.info(f"SessionMiddleware: /start detected, passing through for user {user_id}")
                return await handler(event, data)

            # Allow authorization buttons (Reply keyboard)
            auth_buttons = {
                "✅ Я оплатил",
                "🔄 Проверить снова",
                "❌ Отмена",
                "🚀 Начать работу",
                "🔄 Обновить депозит",
            }
            if actual_event.text in auth_buttons:
                logger.info(
                    f"SessionMiddleware: auth button '{actual_event.text}' detected, passing through for user {user_id}"
                )
                return await handler(event, data)

        # Check FSM state - allow auth states without session
        state: FSMContext | None = data.get("state")
        if state:
            current_state = await state.get_state()
            if current_state:
                # Import auth states
                from bot.states.auth import AuthStates
                from bot.states.registration import RegistrationStates

                auth_state_names = {
                    AuthStates.waiting_for_wallet.state,
                    AuthStates.waiting_for_payment.state,
                    AuthStates.waiting_for_payment_wallet.state,
                }

                # Also allow registration states for new users completing registration
                registration_state_names = {
                    RegistrationStates.waiting_for_financial_password.state,
                    RegistrationStates.waiting_for_password_confirmation.state,
                }

                if current_state in auth_state_names:
                    logger.info(
                        f"SessionMiddleware: auth FSM state '{current_state}', passing through for user {user_id}"
                    )
                    return await handler(event, data)

                if current_state in registration_state_names:
                    logger.info(
                        f"SessionMiddleware: registration FSM state '{current_state}', "
                        f"passing through for user {user_id}"
                    )
                    return await handler(event, data)

        if isinstance(actual_event, CallbackQuery) and actual_event.data:
            logger.debug(f"SessionMiddleware: callback data={actual_event.data!r}")
            if actual_event.data in ("check_payment", "start_after_auth"):
                logger.info(f"SessionMiddleware: auth callback detected, passing through for user {user_id}")
                return await handler(event, data)

        # Check session
        session_key = f"{SESSION_KEY_PREFIX}{user_id}"
        has_session = await self.redis.exists(session_key)

        if not has_session:
            # Session expired or new user
            logger.debug(f"SessionMiddleware: no session for user {user_id}")
            await self._handle_session_expired(actual_event, data)
            return None

        # Update session TTL (sliding window)
        await self.redis.expire(session_key, SESSION_TTL)

        # Check PLEX balance periodically (for users with deposits)
        db_user = data.get("user")
        if db_user:
            await self._check_plex_balance_if_needed(actual_event, data, db_user, user_id)

        return await handler(event, data)

    async def _handle_session_expired(
        self,
        actual_event: Message | CallbackQuery | None,
        data: dict[str, Any],
    ) -> None:
        """Handle expired session."""
        if not actual_event:
            logger.debug("SessionMiddleware: cannot send session expired - no actual event")
            return

        # Reset FSM
        state: FSMContext | None = data.get("state")
        if state:
            await state.clear()

        msg_text = (
            "⏳ Сессия истекла\n\n"
            "Для продолжения работы необходимо оплатить доступ.\n"
            "Пожалуйста, введите /start для начала."
        )

        try:
            if isinstance(actual_event, Message):
                await actual_event.answer(msg_text)
            elif isinstance(actual_event, CallbackQuery):
                if actual_event.message:
                    await actual_event.message.answer(msg_text)
                await actual_event.answer()
        except Exception as e:
            logger.warning(f"Failed to send session expiration message: {e}")

    async def _check_plex_balance_if_needed(
        self,
        actual_event: Message | CallbackQuery | None,
        data: dict[str, Any],
        db_user: Any,
        user_id: int,
    ) -> None:
        """
        Check PLEX balance if check interval passed.

        Only checks once per hour to avoid excessive blockchain calls.
        """
        if not actual_event:
            return

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
                    if isinstance(actual_event, Message):
                        await actual_event.answer(warning)
                    elif isinstance(actual_event, CallbackQuery) and actual_event.message:
                        await actual_event.message.answer(warning)
                except Exception as e:
                    logger.warning(f"Failed to send PLEX warning: {e}")

                logger.warning(f"Insufficient PLEX balance for user {user_id}")

        except Exception as e:
            logger.error(f"PLEX balance check failed for user {user_id}: {e}")
