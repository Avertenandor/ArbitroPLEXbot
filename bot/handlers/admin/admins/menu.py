"""
Admin Management Menu Handler.

Displays the admin management menu with available actions.
"""

from typing import Any

from aiogram import F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import admin_management_keyboard

from .router import router


@router.message(F.text == "👥 Управление админами")
async def show_admin_management(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Show admin management menu.

    Only accessible to super_admin.
    """
    admin = await get_admin_or_deny(message, session, require_super=True, **data)
    if not admin:
        return

    text = """
👥 **Управление админами**

Выберите действие:
    """.strip()

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_management_keyboard(),
    )
