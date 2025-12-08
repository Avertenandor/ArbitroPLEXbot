"""
Knowledge Base Management Handler for Admins.

Allows admins to add, edit, and manage Q&A entries in ARIA's knowledge base.
Source of truth: @VladarevInvestBrok (Босс)
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.knowledge_base import get_knowledge_base
from bot.handlers.admin.utils import get_admin_or_deny

router = Router(name="knowledge_base")


class KBStates(StatesGroup):
    """States for knowledge base management."""

    viewing = State()
    adding_question = State()
    adding_answer = State()
    adding_clarification = State()
    adding_category = State()


def kb_menu_keyboard() -> ReplyKeyboardMarkup:
    """Knowledge base menu keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Все записи")],
            [KeyboardButton(text="➕ Добавить запись")],
            [KeyboardButton(text="🔍 Поиск"), KeyboardButton(text="⚠️ Непроверенные")],
            [KeyboardButton(text="◀️ Назад в админку")],
        ],
        resize_keyboard=True,
    )


def categories_keyboard(categories: list[str]) -> InlineKeyboardMarkup:
    """Categories selection keyboard."""
    buttons = []
    for cat in categories:
        buttons.append([InlineKeyboardButton(
            text=cat, callback_data=f"kb_cat:{cat}"
        )])
    buttons.append([InlineKeyboardButton(
        text="➕ Новая категория", callback_data="kb_cat:__new__"
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def entry_actions_keyboard(entry_id: int, is_boss: bool) -> InlineKeyboardMarkup:
    """Entry actions keyboard."""
    buttons = [
        [InlineKeyboardButton(
            text="✏️ Редактировать", callback_data=f"kb_edit:{entry_id}"
        )],
        [InlineKeyboardButton(
            text="🗑 Удалить", callback_data=f"kb_del:{entry_id}"
        )],
    ]
    if is_boss:
        buttons.append([InlineKeyboardButton(
            text="✅ Подтвердить (Босс)", callback_data=f"kb_verify:{entry_id}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


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
    stats = (
        f"📚 **База знаний ARIA**\n\n"
        f"Всего записей: {len(kb.entries)}\n"
        f"Категорий: {len(kb.get_categories())}\n"
        f"Непроверенных: {len(kb.get_unverified())}\n\n"
        f"_Источник истины: @VladarevInvestBrok_"
    )

    await message.answer(
        stats,
        parse_mode="Markdown",
        reply_markup=kb_menu_keyboard(),
    )


@router.message(KBStates.viewing, F.text == "📋 Все записи")
async def list_all_entries(
    message: Message,
    session: AsyncSession,
    **data: Any,
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


@router.message(KBStates.viewing, F.text == "⚠️ Непроверенные")
async def list_unverified(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """List unverified entries."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    kb = get_knowledge_base()
    unverified = kb.get_unverified()

    if not unverified:
        await message.answer("✅ Все записи проверены Боссом!")
        return

    text = "⚠️ **Непроверенные записи:**\n\n"
    for e in unverified:
        text += f"#{e['id']}: {e['question'][:50]}...\n"
        text += f"  Добавил: @{e.get('added_by', 'unknown')}\n\n"

    text += "_Только Босс может подтверждать записи._"

    await message.answer(text, parse_mode="Markdown")


@router.message(KBStates.viewing, F.text == "➕ Добавить запись")
async def start_add_entry(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Start adding new entry."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    await state.set_state(KBStates.adding_question)
    await state.update_data(adding_by=admin.username or str(admin.telegram_id))

    await message.answer(
        "📝 **Добавление записи в базу знаний**\n\n"
        "Шаг 1/4: Введи **вопрос** (как его задаст пользователь):",
        parse_mode="Markdown",
    )


@router.message(KBStates.adding_question)
async def add_question(message: Message, state: FSMContext) -> None:
    """Save question and ask for answer."""
    await state.update_data(question=message.text)
    await state.set_state(KBStates.adding_answer)

    await message.answer(
        "✅ Вопрос сохранён!\n\n"
        "Шаг 2/4: Введи **ответ** на этот вопрос:",
        parse_mode="Markdown",
    )


@router.message(KBStates.adding_answer)
async def add_answer(message: Message, state: FSMContext) -> None:
    """Save answer and ask for clarification."""
    await state.update_data(answer=message.text)
    await state.set_state(KBStates.adding_clarification)

    await message.answer(
        "✅ Ответ сохранён!\n\n"
        "Шаг 3/4: Введи **разъяснение** для сложных случаев\n"
        "(или отправь `-` чтобы пропустить):",
        parse_mode="Markdown",
    )


@router.message(KBStates.adding_clarification)
async def add_clarification(message: Message, state: FSMContext) -> None:
    """Save clarification and ask for category."""
    clarification = "" if message.text == "-" else message.text
    await state.update_data(clarification=clarification)
    await state.set_state(KBStates.adding_category)

    kb = get_knowledge_base()
    categories = kb.get_categories()

    await message.answer(
        "✅ Разъяснение сохранено!\n\n"
        "Шаг 4/4: Выбери **категорию**:",
        parse_mode="Markdown",
        reply_markup=categories_keyboard(categories),
    )


@router.callback_query(KBStates.adding_category, F.data.startswith("kb_cat:"))
async def select_category(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Handle category selection."""
    category = callback.data.split(":")[1]

    if category == "__new__":
        await callback.message.answer("Введи название новой категории:")
        return

    data = await state.get_data()

    kb = get_knowledge_base()
    entry = kb.add_entry(
        question=data["question"],
        answer=data["answer"],
        category=category,
        clarification=data.get("clarification", ""),
        added_by=data.get("adding_by", "admin"),
    )

    await state.set_state(KBStates.viewing)

    await callback.message.answer(
        f"✅ **Запись #{entry['id']} добавлена!**\n\n"
        f"Категория: {category}\n"
        f"Вопрос: {entry['question'][:50]}...\n\n"
        f"⚠️ Ожидает подтверждения от Босса.",
        parse_mode="Markdown",
        reply_markup=kb_menu_keyboard(),
    )
    await callback.answer()


@router.message(KBStates.adding_category)
async def add_new_category(message: Message, state: FSMContext) -> None:
    """Handle new category input."""
    category = message.text.strip()
    data = await state.get_data()

    kb = get_knowledge_base()
    entry = kb.add_entry(
        question=data["question"],
        answer=data["answer"],
        category=category,
        clarification=data.get("clarification", ""),
        added_by=data.get("adding_by", "admin"),
    )

    await state.set_state(KBStates.viewing)

    await message.answer(
        f"✅ **Запись #{entry['id']} добавлена!**\n\n"
        f"Новая категория: {category}\n"
        f"Вопрос: {entry['question'][:50]}...\n\n"
        f"⚠️ Ожидает подтверждения от Босса.",
        parse_mode="Markdown",
        reply_markup=kb_menu_keyboard(),
    )


@router.message(KBStates.viewing, F.text == "🔍 Поиск")
async def start_search(message: Message) -> None:
    """Start search."""
    await message.answer("🔍 Введи поисковый запрос:")


@router.message(KBStates.viewing, F.text.startswith("/kb_"))
async def view_entry(
    message: Message,
    session: AsyncSession,
    **data: Any,
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

    verified = "✅ Проверено" if entry.get("verified_by_boss") else "⚠️ Не проверено"

    text = (
        f"📋 **Запись #{entry['id']}** {verified}\n\n"
        f"**Категория:** {entry.get('category', 'Общее')}\n\n"
        f"**Вопрос:**\n{entry['question']}\n\n"
        f"**Ответ:**\n{entry['answer']}\n"
    )

    if c := entry.get("clarification"):
        text += f"\n**Разъяснение:**\n{c}\n"

    text += f"\n_Добавил: @{entry.get('added_by', 'system')}_"

    is_boss = admin.role == "super_admin"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=entry_actions_keyboard(entry_id, is_boss),
    )


@router.callback_query(F.data.startswith("kb_verify:"))
async def verify_entry(
    callback: CallbackQuery,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Verify entry (boss only)."""
    admin = await get_admin_or_deny(callback.message, session, **data)
    if not admin or admin.role != "super_admin":
        await callback.answer("Только Босс может подтверждать!", show_alert=True)
        return

    entry_id = int(callback.data.split(":")[1])
    kb = get_knowledge_base()

    if kb.verify_entry(entry_id):
        await callback.message.answer(f"✅ Запись #{entry_id} подтверждена!")
    else:
        await callback.message.answer("Ошибка при подтверждении.")

    await callback.answer()


@router.callback_query(F.data.startswith("kb_del:"))
async def delete_entry(
    callback: CallbackQuery,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Delete entry."""
    admin = await get_admin_or_deny(callback.message, session, **data)
    if not admin:
        return

    entry_id = int(callback.data.split(":")[1])
    kb = get_knowledge_base()

    if kb.delete_entry(entry_id):
        await callback.message.answer(f"🗑 Запись #{entry_id} удалена.")
    else:
        await callback.message.answer("Ошибка при удалении.")

    await callback.answer()


@router.message(KBStates.viewing, F.text == "◀️ Назад в админку")
async def back_to_admin(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Return to admin panel."""
    from bot.handlers.admin.utils import get_admin_keyboard_from_data

    await state.clear()
    await message.answer(
        "👑 Возвращаюсь в админ-панель...",
        reply_markup=get_admin_keyboard_from_data(data),
    )
