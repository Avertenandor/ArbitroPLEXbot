"""
ROI Corridor menu and navigation handlers.

Provides the main menu and navigation functions.
"""

from __future__ import annotations

from typing import Any

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import admin_roi_corridor_menu_keyboard
from bot.utils.admin_utils import clear_state_preserve_admin_token


async def show_roi_corridor_menu(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Show ROI corridor management menu.

    Args:
        message: Message object
        session: Database session
        data: Handler data
    """
    # Verify admin access
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    text = (
        "💰 **Управление коридорами доходности**\n\n"
        "Здесь вы можете настроить параметры начисления дохода "
        "для каждого уровня депозитов.\n\n"
        "**Режимы:**\n"
        "• Custom - случайный процент из коридора для каждого пользователя\n"
        "• Поровну - фиксированный процент для всех пользователей\n\n"
        "**Применение:**\n"
        "• Текущая сессия - изменения применятся к ближайшему начислению\n"
        "• Следующая сессия - изменения применятся через одно начисление\n\n"
        "Выберите действие:"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_roi_corridor_menu_keyboard(),
    )


async def back_to_deposit_management(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Return to deposit management menu.

    Args:
        message: Message object
        state: FSM context
        session: Database session
        data: Handler data
    """
    await clear_state_preserve_admin_token(state)
    from bot.handlers.admin.deposit_management import (
        show_deposit_management_menu,
    )

    await show_deposit_management_menu(message, session, **data)


# Handler registration functions
def register_menu_handlers(router):
    """Register menu handlers to the router."""
    router.message.register(
        show_roi_corridor_menu,
        F.text == "💰 Коридоры доходности"
    )
    router.message.register(
        back_to_deposit_management,
        F.text == "◀️ Назад в управление депозитами"
    )
