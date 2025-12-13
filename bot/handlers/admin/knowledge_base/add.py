"""
Knowledge Base Add Entry Handlers.

Handlers for adding new entries to the knowledge base.
"""

from typing import Any

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.knowledge_base import get_knowledge_base
from bot.handlers.admin.utils import get_admin_or_deny

from .router import KBStates, categories_keyboard, kb_menu_keyboard, router


@router.message(
    KBStates.viewing, F.text.in_(["➕ Добавить", "➕ Добавить запись"])
)
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
    await state.update_data(
        adding_by=admin.username or str(admin.telegram_id)
    )

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


@router.callback_query(
    KBStates.adding_category, F.data.startswith("kb_cat:")
)
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
