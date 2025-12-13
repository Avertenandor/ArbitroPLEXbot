"""
Knowledge Base Edit and Verification Handlers.

Handlers for verifying, unverifying, and requesting rework of entries.
"""

from typing import Any

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.knowledge_base import get_knowledge_base
from bot.handlers.admin.utils import get_admin_or_deny_callback

from .router import KBStates, router


@router.callback_query(F.data.startswith("kb_verify:"))
async def verify_entry(
    callback: CallbackQuery,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Verify entry (boss only)."""
    admin = await get_admin_or_deny_callback(callback, session, **data)
    if not admin or admin.role != "super_admin":
        await callback.answer(
            "Только Босс может подтверждать!", show_alert=True
        )
        return

    entry_id = int(callback.data.split(":")[1])
    kb = get_knowledge_base()

    if kb.verify_entry(entry_id):
        await callback.message.answer(
            f"✅ Запись #{entry_id} подтверждена!"
        )
    else:
        await callback.message.answer("Ошибка при подтверждении.")

    await callback.answer()


@router.callback_query(F.data.startswith("kb_unverify:"))
async def unverify_entry(
    callback: CallbackQuery,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Remove verification from entry (boss only)."""
    admin = await get_admin_or_deny_callback(callback, session, **data)
    if not admin or admin.role != "super_admin":
        await callback.answer("Только Босс!", show_alert=True)
        return

    entry_id = int(callback.data.split(":")[1])
    kb = get_knowledge_base()

    for entry in kb.entries:
        if entry.get("id") == entry_id:
            entry["verified_by_boss"] = False
            kb.save()
            await callback.message.answer(
                f"🔓 Подтверждение снято с записи #{entry_id}"
            )
            break

    await callback.answer()


@router.callback_query(F.data.startswith("kb_rework:"))
async def rework_entry(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Request rework of entry (boss sends comment)."""
    admin = await get_admin_or_deny_callback(callback, session, **data)
    if not admin or admin.role != "super_admin":
        await callback.answer("Только Босс!", show_alert=True)
        return

    entry_id = int(callback.data.split(":")[1])
    await state.update_data(rework_entry_id=entry_id)
    await state.set_state(KBStates.viewing)

    await callback.message.answer(
        f"📝 **Доработка записи #{entry_id}**\n\n"
        "Напиши комментарий что нужно исправить.\n"
        "Комментарий будет добавлен к записи как требование Босса.\n\n"
        "_Или нажми /cancel для отмены_",
        parse_mode="Markdown",
    )
    await callback.answer()
