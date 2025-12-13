"""
Knowledge Base Router and Common Utilities.

Central router for knowledge base management with shared states
and keyboard utilities.
"""

from aiogram import Router
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


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
            [
                KeyboardButton(text="📂 По категориям"),
                KeyboardButton(text="📋 Все записи"),
            ],
            [
                KeyboardButton(text="➕ Добавить"),
                KeyboardButton(text="🔍 Поиск"),
            ],
            [
                KeyboardButton(text="⚠️ На проверку"),
                KeyboardButton(text="🧠 Из диалогов"),
            ],
            [KeyboardButton(text="📊 Статистика БЗ")],
            [KeyboardButton(text="◀️ Назад в админку")],
        ],
        resize_keyboard=True,
    )


def categories_keyboard(categories: list[str]) -> InlineKeyboardMarkup:
    """Categories selection keyboard."""
    buttons = []
    for cat in categories:
        buttons.append(
            [InlineKeyboardButton(text=cat, callback_data=f"kb_cat:{cat}")]
        )
    buttons.append(
        [
            InlineKeyboardButton(
                text="➕ Новая категория", callback_data="kb_cat:__new__"
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def entries_list_keyboard(
    entries: list[dict],
    page: int = 0,
    per_page: int = 5,
    list_type: str = "all",
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
        buttons.append(
            [
                InlineKeyboardButton(
                    text=label, callback_data=f"kb_view:{e['id']}"
                )
            ]
        )

    # Pagination
    nav_row = []
    total_pages = (len(entries) + per_page - 1) // per_page

    if page > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"kb_page:{list_type}:{page - 1}",
            )
        )

    nav_row.append(
        InlineKeyboardButton(
            text=f"{page + 1}/{total_pages}", callback_data="kb_noop"
        )
    )

    if end < len(entries):
        nav_row.append(
            InlineKeyboardButton(
                text="Вперёд ➡️",
                callback_data=f"kb_page:{list_type}:{page + 1}",
            )
        )

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
            buttons.append(
                [
                    InlineKeyboardButton(
                        text="✅ Подтвердить",
                        callback_data=f"kb_verify:{entry_id}",
                    ),
                    InlineKeyboardButton(
                        text="📝 Доработать",
                        callback_data=f"kb_rework:{entry_id}",
                    ),
                ]
            )
        else:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text="🔓 Снять подтверждение",
                        callback_data=f"kb_unverify:{entry_id}",
                    )
                ]
            )

    # Edit and delete buttons
    buttons.append(
        [
            InlineKeyboardButton(
                text="✏️ Редактировать",
                callback_data=f"kb_edit:{entry_id}",
            ),
            InlineKeyboardButton(
                text="🗑 Удалить", callback_data=f"kb_del:{entry_id}"
            ),
        ]
    )

    # Navigation buttons
    buttons.append(
        [
            InlineKeyboardButton(
                text="⬅️ Предыдущая",
                callback_data=f"kb_prev:{entry_id}",
            ),
            InlineKeyboardButton(
                text="➡️ Следующая",
                callback_data=f"kb_next:{entry_id}",
            ),
        ]
    )

    # Back to list
    buttons.append(
        [InlineKeyboardButton(text="📋 К списку", callback_data="kb_list")]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)
