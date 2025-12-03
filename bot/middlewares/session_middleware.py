"""
Session middleware.

Handles Pay-to-Use authorization and session timeouts.
"""

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from aiogram.fsm.context import FSMContext
from loguru import logger
from redis.asyncio import Redis

from app.config.settings import settings

SESSION_TTL = 1500  # 25 minutes
SESSION_KEY_PREFIX = "auth_session:"

class SessionMiddleware(BaseMiddleware):
    def __init__(self, redis: Redis):
        self.redis = redis

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Get user
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)
            
        user_id = user.id
        
        # Allow specific commands/callbacks always
        if isinstance(event, Message) and event.text:
            if event.text.startswith("/start"):
                return await handler(event, data)
                
        if isinstance(event, CallbackQuery) and event.data:
            if event.data == "check_payment" or event.data.startswith("start_"):
                return await handler(event, data)

        # Check session
        session_key = f"{SESSION_KEY_PREFIX}{user_id}"
        has_session = await self.redis.exists(session_key)
        
        if not has_session:
            # Session expired
            if isinstance(event, (Message, CallbackQuery)):
                # Reset FSM
                state: FSMContext = data.get("state")
                if state:
                    await state.clear()
                    
                msg_text = (
                    "⏳ **Сессия истекла**\n\n"
                    "Для продолжения работы необходимо оплатить доступ.\n"
                    "Пожалуйста, введите /start для начала."
                )
                
                try:
                    if isinstance(event, Message):
                        await event.answer(msg_text)
                    elif isinstance(event, CallbackQuery):
                        if event.message:
                            await event.message.answer(msg_text)
                        await event.answer()
                except Exception as e:
                    logger.warning(f"Failed to send session expiration message: {e}")
                        
            # Stop propagation
            return None
            
        # Update session TTL (sliding window)
        await self.redis.expire(session_key, SESSION_TTL)
        
        return await handler(event, data)

