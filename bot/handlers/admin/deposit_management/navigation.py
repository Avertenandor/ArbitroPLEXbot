"""
Deposit Management Navigation Handler

Provides navigation back to admin panel from deposit management:
- Return to admin panel handler
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.utils.admin_utils import clear_state_preserve_admin_token


router = Router(name="admin_deposit_management_navigation")


@router.message(F.text == "◀️ Назад в админ-панель")
@router.message(F.text == "👑 Админ-панель")
async def back_to_admin_panel(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Return to admin panel.

    Args:
        message: Message object
        session: Database session
        state: FSM context
        data: Handler data
    """
    await clear_state_preserve_admin_token(state)
    from bot.handlers.admin.panel import handle_admin_panel_button

    await handle_admin_panel_button(message, session, **data)
