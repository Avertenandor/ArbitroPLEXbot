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
from bot.handlers.admin.utils import get_admin_or_deny, get_admin_or_deny_callback

router = Router(name="knowledge_base")


class KBStates(StatesGroup):
    """States for knowledge base management."""

    viewing = State()
    adding_question = State()
    adding_answer = State()
    adding_clarification = State()
    adding_category = State()
    searching = State()


def kb_menu_keyboard() -> ReplyKeyboardMarkup:
    """Knowledge base menu keyboard - user friendly."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📂 По категориям"), KeyboardButton(text="📋 Все записи")],
            [KeyboardButton(text="➕ Добавить"), KeyboardButton(text="🔍 Поиск")],
            [KeyboardButton(text="⚠️ На проверку"), KeyboardButton(text="🧠 Из диалогов")],
            [KeyboardButton(text="📊 Статистика БЗ")],
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


def entries_list_keyboard(
    entries: list[dict],
    page: int = 0,
    per_page: int = 5,
    list_type: str = "all"
) -> InlineKeyboardMarkup:
    """Generate inline keyboard with entries list for navigation."""
    buttons = []
    
    start = page * per_page
    end = start + per_page
    page_entries = entries[start:end]
    
    for e in page_entries:
        verified = "✅" if e.get("verified_by_boss") else "⚠️"
        learned = "🧠" if e.get("learned_from_dialog") else ""
        label = f"{verified}{learned} #{e['id']}: {e['question'][:35]}..."
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"kb_view:{e['id']}"
        )])
    
    # Pagination
    nav_row = []
    total_pages = (len(entries) + per_page - 1) // per_page
    
    if page > 0:
        nav_row.append(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"kb_page:{list_type}:{page - 1}"
        ))
    
    nav_row.append(InlineKeyboardButton(
        text=f"{page + 1}/{total_pages}",
        callback_data="kb_noop"
    ))
    
    if end < len(entries):
        nav_row.append(InlineKeyboardButton(
            text="Вперёд ➡️",
            callback_data=f"kb_page:{list_type}:{page + 1}"
        ))
    
    if nav_row:
        buttons.append(nav_row)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def entry_actions_keyboard(
    entry_id: int, is_boss: bool, is_verified: bool = False
) -> InlineKeyboardMarkup:
    """Entry actions keyboard with full navigation."""
    buttons = []

    # Boss verification controls
    if is_boss:
        if not is_verified:
            buttons.append([
                InlineKeyboardButton(
                    text="✅ Подтвердить", callback_data=f"kb_verify:{entry_id}"
                ),
                InlineKeyboardButton(
                    text="📝 Доработать", callback_data=f"kb_rework:{entry_id}"
                ),
            ])
        else:
            buttons.append([InlineKeyboardButton(
                text="🔓 Снять подтверждение", callback_data=f"kb_unverify:{entry_id}"
            )])

    # Edit and delete buttons
    buttons.append([
        InlineKeyboardButton(
            text="✏️ Редактировать", callback_data=f"kb_edit:{entry_id}"
        ),
        InlineKeyboardButton(
            text="🗑 Удалить", callback_data=f"kb_del:{entry_id}"
        ),
    ])

    # Navigation buttons
    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Предыдущая", callback_data=f"kb_prev:{entry_id}"
        ),
        InlineKeyboardButton(
            text="➡️ Следующая", callback_data=f"kb_next:{entry_id}"
        ),
    ])

    # Back to list
    buttons.append([InlineKeyboardButton(
        text="📋 К списку", callback_data="kb_list"
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


@router.message(KBStates.viewing, F.text == "📂 По категориям")
async def list_categories(
    message: Message,
    session: AsyncSession,
    **data: Any,
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

    # Build inline keyboard with categories
    buttons = []
    for cat in categories:
        count = len([e for e in kb.entries if e.get("category") == cat])
        buttons.append([InlineKeyboardButton(
            text=f"📂 {cat} ({count})",
            callback_data=f"kb_showcat:{cat[:30]}"
        )])

    await message.answer(
        "📂 **Выбери категорию:**",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data.startswith("kb_showcat:"))
async def show_category_entries(
    callback: CallbackQuery,
    session: AsyncSession,
    **data: Any,
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
    for e in entries[:15]:  # Limit to 15
        verified = "✅" if e.get("verified_by_boss") else "⚠️"
        text += f"{verified} /kb_{e['id']} — {e['question'][:50]}...\n"

    if len(entries) > 15:
        text += f"\n_...и ещё {len(entries) - 15} записей_"

    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()


@router.message(KBStates.viewing, F.text == "🧠 Из диалогов")
async def list_learned_entries(
    message: Message,
    session: AsyncSession,
    **data: Any,
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

    text = f"🧠 **Записи из диалогов ({len(learned)}):**\n\n"
    text += "Нажми на запись чтобы открыть:"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=entries_list_keyboard(learned, page=0, list_type="learned"),
    )


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
        await message.answer("Поиск отменён.", reply_markup=kb_menu_keyboard())
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
    await message.answer(text, parse_mode="Markdown", reply_markup=kb_menu_keyboard())


@router.message(KBStates.viewing, F.text == "⚠️ На проверку")
async def list_unverified(
    message: Message,
    session: AsyncSession,
    **data: Any,
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

    text = f"⚠️ **Записи на проверку ({len(unverified)}):**\n\n"
    text += "Нажми на запись чтобы открыть:"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=entries_list_keyboard(unverified, page=0, list_type="unverified"),
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


@router.message(KBStates.viewing, F.text.in_(["➕ Добавить", "➕ Добавить запись"]))
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
    is_verified = entry.get("verified_by_boss", False)

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=entry_actions_keyboard(entry_id, is_boss, is_verified),
    )


@router.callback_query(F.data.startswith("kb_verify:"))
async def verify_entry(
    callback: CallbackQuery,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Verify entry (boss only)."""
    admin = await get_admin_or_deny_callback(callback, session, **data)
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


@router.callback_query(F.data.startswith("kb_prev:"))
async def prev_entry(
    callback: CallbackQuery,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Navigate to previous entry."""
    admin = await get_admin_or_deny_callback(callback, session, **data)
    if not admin:
        return

    current_id = int(callback.data.split(":")[1])
    kb = get_knowledge_base()

    # Find previous entry
    ids = sorted(e.get("id", 0) for e in kb.entries)
    current_idx = ids.index(current_id) if current_id in ids else 0
    prev_idx = (current_idx - 1) % len(ids)
    prev_id = ids[prev_idx]

    entry = next((e for e in kb.entries if e.get("id") == prev_id), None)
    if entry:
        await show_entry(callback.message, entry, admin, edit=True)

    await callback.answer()


@router.callback_query(F.data.startswith("kb_next:"))
async def next_entry(
    callback: CallbackQuery,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Navigate to next entry."""
    admin = await get_admin_or_deny_callback(callback, session, **data)
    if not admin:
        return

    current_id = int(callback.data.split(":")[1])
    kb = get_knowledge_base()

    # Find next entry
    ids = sorted(e.get("id", 0) for e in kb.entries)
    current_idx = ids.index(current_id) if current_id in ids else 0
    next_idx = (current_idx + 1) % len(ids)
    next_id = ids[next_idx]

    entry = next((e for e in kb.entries if e.get("id") == next_id), None)
    if entry:
        await show_entry(callback.message, entry, admin, edit=True)

    await callback.answer()


@router.callback_query(F.data.startswith("kb_view:"))
async def view_entry_callback(
    callback: CallbackQuery,
    session: AsyncSession,
    **data: Any,
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
    callback: CallbackQuery,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Handle pagination for entries list."""
    admin = await get_admin_or_deny_callback(callback, session, **data)
    if not admin:
        return

    parts = callback.data.split(":")
    list_type = parts[1]
    page = int(parts[2])

    kb = get_knowledge_base()

    if list_type == "unverified":
        entries = kb.get_unverified()
        title = f"⚠️ **Записи на проверку ({len(entries)}):**"
    elif list_type == "learned":
        entries = [e for e in kb.entries if e.get("learned_from_dialog")]
        title = f"🧠 **Записи из диалогов ({len(entries)}):**"
    elif list_type == "all":
        entries = kb.entries
        title = f"📚 **Все записи ({len(entries)}):**"
    else:
        entries = kb.entries
        title = "📚 **Записи:**"

    text = f"{title}\n\nНажми на запись чтобы открыть:"

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
    callback: CallbackQuery,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Go back to entries list."""
    admin = await get_admin_or_deny_callback(callback, session, **data)
    if not admin:
        return

    kb = get_knowledge_base()
    entries = kb.entries

    text = f"📚 **Все записи ({len(entries)}):**\n\nНажми на запись чтобы открыть:"

    await callback.message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=entries_list_keyboard(entries, page=0, list_type="all"),
    )
    await callback.answer()


async def show_entry(message: Message, entry: dict, admin, edit: bool = False):
    """Helper to display entry with keyboard."""
    verified = "✅ Проверено" if entry.get("verified_by_boss") else "⚠️ Не проверено"

    text = (
        f"📋 **Запись #{entry['id']}** {verified}\n\n"
        f"**Категория:** {entry.get('category', 'Общее')}\n\n"
        f"**Вопрос:**\n{entry['question']}\n\n"
        f"**Ответ:**\n{entry['answer']}\n"
    )

    if c := entry.get("clarification"):
        text += f"\n**Разъяснение:**\n{c}\n"

    if rework := entry.get("boss_rework_comment"):
        text += f"\n⚠️ **Комментарий Босса:**\n_{rework}_\n"

    text += f"\n_Добавил: @{entry.get('added_by', 'system')}_"

    is_boss = admin.role == "super_admin"
    is_verified = entry.get("verified_by_boss", False)

    if edit:
        await message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=entry_actions_keyboard(entry["id"], is_boss, is_verified),
        )
    else:
        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=entry_actions_keyboard(entry["id"], is_boss, is_verified),
        )


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


# ============ GLOBAL COMMAND HANDLER (works from any state) ============

@router.message(F.text.regexp(r"^/kb_(\d+)$"))
async def view_entry_global(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """View specific entry from ANY state (global command)."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    # Extract entry_id from command
    import re
    match = re.match(r"^/kb_(\d+)$", message.text)
    if not match:
        return
    
    entry_id = int(match.group(1))
    kb = get_knowledge_base()
    entry = next((e for e in kb.entries if e.get("id") == entry_id), None)

    if not entry:
        await message.answer(f"❌ Запись #{entry_id} не найдена.")
        return

    # Set state to viewing for proper context
    await state.set_state(KBStates.viewing)

    verified = "✅ Проверено Боссом" if entry.get("verified_by_boss") else "⚠️ Ожидает проверки"
    learned = "🧠 Из диалога" if entry.get("learned_from_dialog") else ""

    text = (
        f"📋 **Запись #{entry['id']}**\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📁 **Категория:** {entry.get('category', 'Общее')}\n"
        f"📌 **Статус:** {verified} {learned}\n\n"
        f"❓ **Вопрос:**\n{entry['question']}\n\n"
        f"💬 **Ответ:**\n{entry['answer']}\n"
    )

    if c := entry.get("clarification"):
        text += f"\n📝 **Уточнение:**\n{c}\n"

    text += f"\n━━━━━━━━━━━━━━━━━━\n"
    text += f"👤 Добавил: @{entry.get('added_by', 'system')}\n"
    
    if source := entry.get("source_user"):
        text += f"💬 Источник: @{source}\n"

    is_boss = admin.role == "super_admin"
    is_verified = entry.get("verified_by_boss", False)

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=entry_actions_keyboard(entry_id, is_boss, is_verified),
    )
