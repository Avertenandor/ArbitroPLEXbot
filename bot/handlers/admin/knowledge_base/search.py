"""
Knowledge Base Search Handlers.

Handlers for searching entries in the knowledge base.
"""

from typing import Any

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.knowledge_base import get_knowledge_base
from bot.handlers.admin.utils import get_admin_or_deny

from .router import KBStates, kb_menu_keyboard, router


@router.message(KBStates.viewing, F.text == "🔍 Поиск")
async def start_search(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Start search mode."""
    await state.set_state(KBStates.searching)
    await message.answer(
        "🔍 **Поиск по базе знаний**\n\n"
        "Введи слово или фразу для поиска:\n"
        "_Например: депозит, PLEX, арбитраж_\n\n"
        "Или нажми /cancel для отмены"
    )


@router.message(KBStates.searching)
async def do_search(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Perform search."""
    if message.text == "/cancel":
        await state.set_state(KBStates.viewing)
        await message.answer(
            "Поиск отменён.", reply_markup=kb_menu_keyboard()
        )
        return

    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    kb = get_knowledge_base()
    results = kb.search(message.text)

    if not results:
        await message.answer(
            f"🔍 По запросу «{message.text}» ничего не найдено.\n"
            "Попробуй другой запрос или /cancel"
        )
        return

    text = f"🔍 **Найдено: {len(results)}**\n\n"
    for e in results[:10]:
        verified = "✅" if e.get("verified_by_boss") else "⚠️"
        text += f"{verified} /kb_{e['id']} — {e['question'][:50]}...\n"

    if len(results) > 10:
        text += f"\n_...и ещё {len(results) - 10}_"

    await state.set_state(KBStates.viewing)
    await message.answer(
        text, parse_mode="Markdown", reply_markup=kb_menu_keyboard()
    )
