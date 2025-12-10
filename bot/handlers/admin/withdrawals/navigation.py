"""
Admin Withdrawals - Navigation Handlers.

Handles navigation between withdrawal views.
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.states.admin_states import AdminStates


router = Router(name="admin_withdrawals_navigation")


@router.message(F.text == "◀️ Назад к выводам")
@router.message(F.text == "❌ Нет, отменить", AdminStates.confirming_withdrawal_action)
async def handle_cancel_withdrawal_action(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Cancel withdrawal action and return to list."""
    # Import here to avoid circular dependency
    from bot.handlers.admin.withdrawals.pending import handle_pending_withdrawals

    # Re-use logic to show list
    await handle_pending_withdrawals(message, session, state, **data)


@router.message(AdminStates.viewing_withdrawal, F.text == "◀️ Назад к списку")
async def handle_back_to_list(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Return to withdrawal list."""
    # Import here to avoid circular dependency
    from bot.handlers.admin.withdrawals.pending import handle_pending_withdrawals

    await handle_pending_withdrawals(message, session, state, **data)


@router.message(F.text == "👑 Админ-панель")
async def handle_back_to_admin_panel(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Return to admin panel from withdrawals menu"""
    from bot.handlers.admin.panel import handle_admin_panel_button

    await handle_admin_panel_button(message, session, **data)
