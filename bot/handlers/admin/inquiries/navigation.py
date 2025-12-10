"""
Admin Inquiry Navigation Handlers.

Handles navigation between inquiry views:
- Back to list
- Back to inquiries menu
- Refresh list
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession


router = Router(name="admin_inquiry_navigation")


# ============================================================================
# NAVIGATION
# ============================================================================


@router.message(StateFilter("*"), F.text == "◀️ Назад к списку")
async def handle_back_to_list(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Return to inquiry list."""
    is_admin = data.get("is_admin", False)
    if not is_admin:
        return

    state_data = await state.get_data()
    inquiry_type = state_data.get("inquiry_type", "new")

    # Import handlers here to avoid circular imports
    from bot.handlers.admin.inquiries.lists import (
        handle_closed_inquiries,
        handle_my_inquiries,
        handle_new_inquiries,
    )

    # Redirect to appropriate list
    if inquiry_type == "my":
        await handle_my_inquiries(message, state, session, **data)
    elif inquiry_type == "closed":
        await handle_closed_inquiries(message, state, session, **data)
    else:
        await handle_new_inquiries(message, state, session, **data)


@router.message(StateFilter("*"), F.text == "◀️ Назад к обращениям")
async def handle_back_to_inquiries_menu(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Return to inquiries main menu."""
    # Import handler here to avoid circular imports
    from bot.handlers.admin.inquiries.menu import handle_admin_inquiries_menu

    await handle_admin_inquiries_menu(message, state, session, **data)


@router.message(StateFilter("*"), F.text == "🔄 Обновить список")
async def handle_refresh_list(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Refresh current inquiry list."""
    state_data = await state.get_data()
    inquiry_type = state_data.get("inquiry_type", "new")

    # Import handlers here to avoid circular imports
    from bot.handlers.admin.inquiries.lists import (
        handle_closed_inquiries,
        handle_my_inquiries,
        handle_new_inquiries,
    )

    if inquiry_type == "my":
        await handle_my_inquiries(message, state, session, **data)
    elif inquiry_type == "closed":
        await handle_closed_inquiries(message, state, session, **data)
    else:
        await handle_new_inquiries(message, state, session, **data)
