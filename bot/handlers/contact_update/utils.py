"""
Contact Update Utilities.

Helper functions for contact update operations.
"""

from typing import Any

from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_user_or_error(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> User | None:
    """
    Get user from handler data or show error.

    Args:
        message: Telegram message
        state: FSM state
        **data: Handler data

    Returns:
        User object or None if not found
    """
    user: User | None = data.get("user")
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        await state.clear()
        return None
    return user


async def navigate_to_home(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Navigate to main menu (consolidated handler)."""
    user: User | None = data.get("user")
    if not user:
        await state.clear()
        return

    await state.clear()

    from bot.handlers.menu import show_main_menu

    await show_main_menu(message, session, user, state, **data)
