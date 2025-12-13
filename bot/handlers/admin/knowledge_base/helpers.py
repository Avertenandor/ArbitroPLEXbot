"""
Knowledge Base View Helpers.

Shared helper functions for displaying and formatting entries.
"""
from aiogram.types import Message

from .router import entry_actions_keyboard


async def show_entry(message: Message, entry: dict, admin, edit: bool = False):
    """Helper to display entry with keyboard."""
    verified = (
        "✅ Проверено" if entry.get("verified_by_boss") else "⚠️ Не проверено"
    )

    text = (
        f"📋 **Запись #{entry['id']}** {verified}\n\n"
        f"**Категория:** {entry.get('category', 'Общее')}\n\n"
        f"**Вопрос:**\n{entry['question']}\n\n"
        f"**Ответ:**\n{entry['answer']}\n"
    )

    if clarification := entry.get("clarification"):
        text += f"\n**Разъяснение:**\n{clarification}\n"

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


def format_entry_text_extended(entry: dict, admin) -> tuple[str, bool, bool]:
    """Format extended entry text for global view.

    Returns: (text, is_boss, is_verified)
    """
    verified = (
        "✅ Проверено Боссом"
        if entry.get("verified_by_boss")
        else "⚠️ Ожидает проверки"
    )
    learned = "🧠 Из диалога" if entry.get("learned_from_dialog") else ""

    text = (
        f"📋 **Запись #{entry['id']}**\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📁 **Категория:** {entry.get('category', 'Общее')}\n"
        f"📌 **Статус:** {verified} {learned}\n\n"
        f"❓ **Вопрос:**\n{entry['question']}\n\n"
        f"💬 **Ответ:**\n{entry['answer']}\n"
    )

    if clarification := entry.get("clarification"):
        text += f"\n📝 **Уточнение:**\n{clarification}\n"

    text += "\n━━━━━━━━━━━━━━━━━━\n"
    text += f"👤 Добавил: @{entry.get('added_by', 'system')}\n"

    if source := entry.get("source_user"):
        text += f"💬 Источник: @{source}\n"

    is_boss = admin.role == "super_admin"
    is_verified = entry.get("verified_by_boss", False)

    return text, is_boss, is_verified
