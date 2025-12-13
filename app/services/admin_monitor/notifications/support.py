"""
Admin Event Monitor - Support Notifications.

This module provides notification methods for support-related events:
- Support tickets
- User inquiries
- Appeals
"""

from typing import TYPE_CHECKING

from ..constants import EventCategory, EventPriority


if TYPE_CHECKING:
    from ..monitor import AdminEventMonitor


async def notify_new_support_ticket(
    monitor: "AdminEventMonitor",
    ticket_id: int,
    user_id: int,
    category: str,
) -> int:
    """Уведомление о новом тикете поддержки."""
    return await monitor.notify(
        category=EventCategory.SUPPORT,
        priority=EventPriority.MEDIUM,
        title="Новое обращение в поддержку",
        details={
            "Тикет": f"#{ticket_id}",
            "Пользователь": user_id,
            "Категория": category,
        },
        footer="Перейдите в админ-панель для обработки",
    )


async def notify_new_inquiry(
    monitor: "AdminEventMonitor",
    inquiry_id: int,
    user_id: int,
    username: str | None,
    question_preview: str,
) -> int:
    """Уведомление о новом вопросе пользователя."""
    question_text = (
        question_preview[:80] + "..."
        if len(question_preview) > 80
        else question_preview
    )
    return await monitor.notify(
        category=EventCategory.INQUIRY,
        priority=EventPriority.MEDIUM,
        title="Новый вопрос от пользователя",
        details={
            "ID обращения": inquiry_id,
            "Пользователь": f"{user_id} (@{username or 'нет'})",
            "Вопрос": question_text,
        },
        footer="Нажмите «❓ Вопросы пользователей» в админ-панели",
    )


async def notify_appeal_created(
    monitor: "AdminEventMonitor",
    appeal_id: int,
    user_id: int,
    username: str | None,
    subject: str,
) -> int:
    """Уведомление о новой апелляции."""
    return await monitor.notify(
        category=EventCategory.APPEAL,
        priority=EventPriority.HIGH,
        title="Новая апелляция",
        details={
            "ID апелляции": appeal_id,
            "Пользователь": f"{user_id} (@{username or 'нет'})",
            "Тема": subject[:80],
        },
        footer="Апелляции требуют приоритетного рассмотрения",
    )
