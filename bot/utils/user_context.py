"""
User context utilities for bot handlers.

Provides helper functions to reduce code duplication when loading users
from message/callback context.
"""

from typing import Any, Union

from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from bot.utils.user_loader import UserLoader


async def get_user_from_context(
    event: Union[Message, CallbackQuery],
    session: AsyncSession,
    data: dict[str, Any],
) -> User | None:
    """
    Get user from context data or load from database.

    This function encapsulates the common pattern of loading a user:
    1. First, check if user exists in the data dict (from middleware)
    2. If not found, extract telegram_id from message/callback
    3. Load user from database using telegram_id
    4. Return User or None if not found

    Args:
        event: Message or CallbackQuery from aiogram
        session: Database session
        data: Handler data dictionary (usually from **data in handler)

    Returns:
        User object or None if not found

    Example:
        >>> user = await get_user_from_context(message, session, data)
        >>> if not user:
        >>>     await message.answer(get_text('errors.user_load_error'))
        >>>     return
    """
    # Try to get user from context data first (injected by middleware)
    user: User | None = data.get("user")
    if user:
        return user

    # Extract telegram_id from event
    telegram_id = None
    if isinstance(event, Message):
        telegram_id = event.from_user.id if event.from_user else None
    elif isinstance(event, CallbackQuery):
        telegram_id = event.from_user.id if event.from_user else None

    # Load from database if telegram_id is available
    if telegram_id:
        user = await UserLoader.get_user_by_telegram_id(session, telegram_id)

    return user
