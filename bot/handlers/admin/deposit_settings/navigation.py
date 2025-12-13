"""Navigation handlers for deposit settings."""

from typing import Any

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession


router = Router()


@router.message(F.text == "👑 Админ-панель")
async def handle_back_to_admin_panel(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Return to admin panel from deposit settings menu."""
    from bot.handlers.admin.panel import handle_admin_panel_button

    await handle_admin_panel_button(message, session, **data)
