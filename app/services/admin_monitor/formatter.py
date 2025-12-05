"""
Admin Event Monitor - Message Formatter.

This module handles formatting of notification messages for administrators.
Messages are formatted in Russian with proper emoji support and value formatting.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from .constants import (
    CATEGORY_EMOJI,
    CATEGORY_NAMES_RU,
    PRIORITY_EMOJI,
    PRIORITY_NAMES_RU,
    EventCategory,
    EventPriority,
)


def format_admin_message(
    category: EventCategory,
    priority: EventPriority,
    title: str,
    details: dict[str, Any],
    footer: str | None = None,
) -> str:
    """
    Форматировать сообщение для отправки администраторам.

    Args:
        category: Категория события
        priority: Приоритет
        title: Заголовок
        details: Детали события (ключ-значение)
        footer: Дополнительный текст в конце

    Returns:
        Отформатированное сообщение
    """
    cat_emoji = CATEGORY_EMOJI.get(category, "📋")
    cat_name = CATEGORY_NAMES_RU.get(category, category.value)
    prio_emoji = PRIORITY_EMOJI.get(priority, "⚪")
    prio_name = PRIORITY_NAMES_RU.get(priority, priority.value)

    # Заголовок
    lines = [
        f"{cat_emoji} *{title}*",
        f"{prio_emoji} Приоритет: {prio_name}",
        f"📂 Категория: {cat_name}",
        "",
    ]

    # Детали
    for key, value in details.items():
        if value is not None:
            # Форматирование значений
            formatted_value = _format_value(value)
            lines.append(f"• {key}: `{formatted_value}`")

    # Время события
    lines.append("")
    lines.append(f"🕐 {datetime.now(UTC).strftime('%d.%m.%Y %H:%M:%S')} UTC")

    # Футер
    if footer:
        lines.append("")
        lines.append(f"_{footer}_")

    return "\n".join(lines)


def _format_value(value: Any) -> str:
    """
    Форматировать значение для отображения.

    Args:
        value: Значение для форматирования

    Returns:
        Отформатированная строка
    """
    if isinstance(value, Decimal):
        return f"{value:,.4f}".rstrip("0").rstrip(".")
    elif isinstance(value, datetime):
        return value.strftime("%d.%m.%Y %H:%M:%S")
    elif isinstance(value, bool):
        return "Да" if value else "Нет"
    else:
        return str(value)
