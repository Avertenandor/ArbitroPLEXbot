"""
Knowledge Base Menu Handlers.

Handlers for main menu, statistics, and navigation to admin panel.
"""

from typing import Any

from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.knowledge_base import get_knowledge_base
from bot.handlers.admin.utils import get_admin_or_deny

from .router import KBStates, kb_menu_keyboard, router


@router.message(StateFilter("*"), F.text == "📚 База знаний")
async def open_knowledge_base(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Open knowledge base management."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    await state.set_state(KBStates.viewing)

    kb = get_knowledge_base()
    learned = len([e for e in kb.entries if e.get("learned_from_dialog")])

    stats = (
        f"📚 **База знаний ARIA**\n\n"
        f"📋 Всего записей: **{len(kb.entries)}**\n"
        f"📂 Категорий: **{len(kb.get_categories())}**\n"
        f"⚠️ На проверку: **{len(kb.get_unverified())}**\n"
        f"🧠 Из диалогов: **{learned}**\n\n"
        f"_Источник истины: @VladarevInvestBrok_\n\n"
        f"Выбери действие:"
    )

    await message.answer(
        stats,
        parse_mode="Markdown",
        reply_markup=kb_menu_keyboard(),
    )


@router.message(KBStates.viewing, F.text == "📊 Статистика БЗ")
async def kb_statistics(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show knowledge base statistics."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    kb = get_knowledge_base()

    # Count by category
    cat_stats = {}
    for e in kb.entries:
        cat = e.get("category", "Без категории")
        cat_stats[cat] = cat_stats.get(cat, 0) + 1

    # Count verified vs unverified
    verified = len([e for e in kb.entries if e.get("verified_by_boss")])
    unverified = len(kb.entries) - verified
    learned = len([e for e in kb.entries if e.get("learned_from_dialog")])

    text = "📊 **Статистика Базы Знаний**\n\n"
    text += f"📋 Всего записей: **{len(kb.entries)}**\n"
    text += f"✅ Подтверждённых: **{verified}**\n"
    text += f"⚠️ На проверку: **{unverified}**\n"
    text += f"🧠 Из диалогов с ARIA: **{learned}**\n\n"

    text += "📂 **По категориям:**\n"
    for cat, count in sorted(cat_stats.items()):
        text += f"  • {cat}: {count}\n"

    await message.answer(text, parse_mode="Markdown")


@router.message(KBStates.viewing, F.text == "◀️ Назад в админку")
async def back_to_admin(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Return to admin panel."""
    from bot.handlers.admin.utils import get_admin_keyboard_from_data
    from bot.utils.admin_utils import clear_state_preserve_admin_token

    # Возвращаемся в админку, не теряя admin_session_token.
    await clear_state_preserve_admin_token(state)
    await message.answer(
        "👑 Возвращаюсь в админ-панель...",
        reply_markup=get_admin_keyboard_from_data(data),
    )
