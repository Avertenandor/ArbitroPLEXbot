"""
Admin List Handler.

Displays a list of all administrators with their roles and information.
"""

from typing import Any

from aiogram import F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin_service import AdminService
from bot.handlers.admin.utils.admin_checks import (
    format_role_display,
    get_admin_or_deny,
)
from bot.keyboards.reply import admin_management_keyboard

from .router import router


@router.message(F.text == "📋 Список админов")
async def handle_list_admins(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Show list of all admins.

    Only accessible to super_admin.
    """
    admin = await get_admin_or_deny(message, session, require_super=True, **data)
    if not admin:
        return

    admin_service = AdminService(session)
    admins = await admin_service.list_all_admins()

    if not admins:
        await message.answer("📋 Список админов пуст")
        return

    text = "📋 **Список админов**\n\n"

    for idx, a in enumerate(admins, 1):
        role_display = await format_role_display(a.role)

        creator_info = ""
        if a.created_by:
            creator = await admin_service.get_admin_by_id(a.created_by)
            if creator:
                creator_info = f" (создан {creator.display_name})"

        text += (
            f"{idx}. {a.display_name}\n"
            f"   ID: `{a.telegram_id}`\n"
            f"   Роль: {role_display}{creator_info}\n\n"
        )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_management_keyboard(),
    )
