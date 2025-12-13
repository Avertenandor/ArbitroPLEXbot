"""
Knowledge Base Delete Handler.

Handler for deleting entries from the knowledge base.
"""

from typing import Any

from aiogram import F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.knowledge_base import get_knowledge_base
from bot.handlers.admin.utils import get_admin_or_deny_callback

from .router import router


@router.callback_query(F.data.startswith("kb_del:"))
async def delete_entry(
    callback: CallbackQuery,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Delete entry."""
    admin = await get_admin_or_deny_callback(callback, session, **data)
    if not admin:
        return

    entry_id = int(callback.data.split(":")[1])
    kb = get_knowledge_base()

    if kb.delete_entry(entry_id):
        await callback.message.answer(f"🗑 Запись #{entry_id} удалена.")
    else:
        await callback.message.answer("Ошибка при удалении.")

    await callback.answer()
