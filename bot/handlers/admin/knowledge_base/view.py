"""
Knowledge Base View and Navigation Handlers.

Handlers for viewing entries, categories, lists, and navigation.
"""
import re
from typing import Any

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.knowledge_base import get_knowledge_base
from bot.handlers.admin.utils import get_admin_or_deny, get_admin_or_deny_callback

from .helpers import format_entry_text_extended, show_entry
from .router import KBStates, entries_list_keyboard, entry_actions_keyboard, router


@router.message(KBStates.viewing, F.text == "📂 По категориям")
async def list_categories(
    message: Message, session: AsyncSession, **data: Any
) -> None:
    """List all categories with entry counts."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    kb = get_knowledge_base()
    categories = kb.get_categories()
    if not categories:
        await message.answer("Категорий пока нет.")
        return

    buttons = []
    for cat in categories:
        count = len([e for e in kb.entries if e.get("category") == cat])
        buttons.append([
            InlineKeyboardButton(
                text=f"📂 {cat} ({count})",
                callback_data=f"kb_showcat:{cat[:30]}",
            )
        ])

    await message.answer(
        "📂 **Выбери категорию:**",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data.startswith("kb_showcat:"))
async def show_category_entries(
    callback: CallbackQuery, session: AsyncSession, **data: Any
) -> None:
    """Show entries in selected category."""
    admin = await get_admin_or_deny_callback(callback, session, **data)
    if not admin:
        return

    category = callback.data.split(":")[1]
    kb = get_knowledge_base()
    entries = [e for e in kb.entries if e.get("category", "").startswith(category)]

    if not entries:
        await callback.message.answer(f"В категории '{category}' нет записей.")
        await callback.answer()
        return

    text = f"📂 **{category}** ({len(entries)} записей)\n\n"
    for e in entries[:15]:
        verified = "✅" if e.get("verified_by_boss") else "⚠️"
        text += f"{verified} /kb_{e['id']} — {e['question'][:50]}...\n"

    if len(entries) > 15:
        text += f"\n_...и ещё {len(entries) - 15} записей_"

    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()


@router.message(KBStates.viewing, F.text == "🧠 Из диалогов")
async def list_learned_entries(
    message: Message, session: AsyncSession, **data: Any
) -> None:
    """List entries learned from dialogs."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    kb = get_knowledge_base()
    learned = [e for e in kb.entries if e.get("learned_from_dialog")]

    if not learned:
        await message.answer(
            "🧠 **Записей из диалогов пока нет.**\n\n"
            "ARIA извлекает знания из свободных диалогов с Боссом и админами.\n\n"
            "Как это работает:\n"
            "1. Войди в 🤖 AI Помощник → 💬 Свободный диалог\n"
            "2. Расскажи ARIA что-то новое о платформе\n"
            "3. Нажми «Завершить диалог»\n"
            "4. ARIA извлечёт и сохранит знания",
            parse_mode="Markdown",
        )
        return

    text = f"🧠 **Записи из диалогов ({len(learned)}):**\n\nНажми на запись:"
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=entries_list_keyboard(learned, page=0, list_type="learned"),
    )


@router.message(KBStates.viewing, F.text == "⚠️ На проверку")
async def list_unverified(
    message: Message, session: AsyncSession, **data: Any
) -> None:
    """List entries pending verification."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    kb = get_knowledge_base()
    unverified = kb.get_unverified()

    if not unverified:
        await message.answer("✅ **Все записи проверены!**", parse_mode="Markdown")
        return

    text = f"⚠️ **Записи на проверку ({len(unverified)}):**\n\nНажми на запись:"
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=entries_list_keyboard(unverified, page=0, list_type="unverified"),
    )


@router.message(KBStates.viewing, F.text == "📋 Все записи")
async def list_all_entries(
    message: Message, session: AsyncSession, **data: Any
) -> None:
    """List all knowledge base entries."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    kb = get_knowledge_base()
    if not kb.entries:
        await message.answer("База знаний пуста.")
        return

    text = "📚 **Все записи:**\n\n"
    for cat in kb.get_categories():
        text += f"📂 **{cat}**\n"
        for e in kb.entries:
            if e.get("category") == cat:
                verified = "✅" if e.get("verified_by_boss") else "⚠️"
                text += f"  {verified} #{e['id']}: {e['question'][:40]}...\n"
        text += "\n"

    text += "_Нажми на номер для просмотра: /kb_1, /kb_2..._"
    await message.answer(text, parse_mode="Markdown")


@router.message(KBStates.viewing, F.text.startswith("/kb_"))
async def view_entry(
    message: Message, session: AsyncSession, **data: Any
) -> None:
    """View specific entry."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    try:
        entry_id = int(message.text.replace("/kb_", ""))
    except ValueError:
        return

    kb = get_knowledge_base()
    entry = next((e for e in kb.entries if e.get("id") == entry_id), None)
    if not entry:
        await message.answer("Запись не найдена.")
        return

    await show_entry(message, entry, admin, edit=False)


@router.callback_query(F.data.startswith("kb_prev:"))
async def prev_entry(
    callback: CallbackQuery, session: AsyncSession, **data: Any
) -> None:
    """Navigate to previous entry."""
    admin = await get_admin_or_deny_callback(callback, session, **data)
    if not admin:
        return

    current_id = int(callback.data.split(":")[1])
    kb = get_knowledge_base()

    ids = sorted(e.get("id", 0) for e in kb.entries)
    current_idx = ids.index(current_id) if current_id in ids else 0
    prev_id = ids[(current_idx - 1) % len(ids)]

    entry = next((e for e in kb.entries if e.get("id") == prev_id), None)
    if entry:
        await show_entry(callback.message, entry, admin, edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("kb_next:"))
async def next_entry(
    callback: CallbackQuery, session: AsyncSession, **data: Any
) -> None:
    """Navigate to next entry."""
    admin = await get_admin_or_deny_callback(callback, session, **data)
    if not admin:
        return

    current_id = int(callback.data.split(":")[1])
    kb = get_knowledge_base()

    ids = sorted(e.get("id", 0) for e in kb.entries)
    current_idx = ids.index(current_id) if current_id in ids else 0
    next_id = ids[(current_idx + 1) % len(ids)]

    entry = next((e for e in kb.entries if e.get("id") == next_id), None)
    if entry:
        await show_entry(callback.message, entry, admin, edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("kb_view:"))
async def view_entry_callback(
    callback: CallbackQuery, session: AsyncSession, **data: Any
) -> None:
    """View entry by inline button click."""
    admin = await get_admin_or_deny_callback(callback, session, **data)
    if not admin:
        return

    entry_id = int(callback.data.split(":")[1])
    kb = get_knowledge_base()
    entry = next((e for e in kb.entries if e.get("id") == entry_id), None)

    if not entry:
        await callback.answer("Запись не найдена", show_alert=True)
        return

    await show_entry(callback.message, entry, admin, edit=False)
    await callback.answer()


@router.callback_query(F.data.startswith("kb_page:"))
async def paginate_entries(
    callback: CallbackQuery, session: AsyncSession, **data: Any
) -> None:
    """Handle pagination for entries list."""
    admin = await get_admin_or_deny_callback(callback, session, **data)
    if not admin:
        return

    parts = callback.data.split(":")
    list_type, page = parts[1], int(parts[2])
    kb = get_knowledge_base()

    if list_type == "unverified":
        entries = kb.get_unverified()
        title = f"⚠️ **Записи на проверку ({len(entries)}):**"
    elif list_type == "learned":
        entries = [e for e in kb.entries if e.get("learned_from_dialog")]
        title = f"🧠 **Записи из диалогов ({len(entries)}):**"
    else:
        entries = kb.entries
        title = f"📚 **Все записи ({len(entries)}):**"

    text = f"{title}\n\nНажми на запись:"
    try:
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=entries_list_keyboard(entries, page=page, list_type=list_type),
        )
    except Exception:
        await callback.message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=entries_list_keyboard(entries, page=page, list_type=list_type),
        )
    await callback.answer()


@router.callback_query(F.data == "kb_noop")
async def noop_callback(callback: CallbackQuery) -> None:
    """Do nothing (for page indicator)."""
    await callback.answer()


@router.callback_query(F.data == "kb_list")
async def back_to_list(
    callback: CallbackQuery, session: AsyncSession, **data: Any
) -> None:
    """Go back to entries list."""
    admin = await get_admin_or_deny_callback(callback, session, **data)
    if not admin:
        return

    kb = get_knowledge_base()
    text = f"📚 **Все записи ({len(kb.entries)}):**\n\nНажми на запись:"
    await callback.message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=entries_list_keyboard(kb.entries, page=0, list_type="all"),
    )
    await callback.answer()


@router.message(F.text.regexp(r"^/kb_(\d+)$"))
async def view_entry_global(
    message: Message, session: AsyncSession, state: FSMContext, **data: Any
) -> None:
    """View specific entry from ANY state (global command)."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    match = re.match(r"^/kb_(\d+)$", message.text)
    if not match:
        return

    entry_id = int(match.group(1))
    kb = get_knowledge_base()
    entry = next((e for e in kb.entries if e.get("id") == entry_id), None)

    if not entry:
        await message.answer(f"❌ Запись #{entry_id} не найдена.")
        return

    await state.set_state(KBStates.viewing)

    text, is_boss, is_verified = format_entry_text_extended(entry, admin)
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=entry_actions_keyboard(entry_id, is_boss, is_verified),
    )
