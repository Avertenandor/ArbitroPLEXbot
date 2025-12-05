"""
Notification helpers for inquiry handlers.

This module contains helper functions for sending notifications to admins
about new inquiries and updates.
"""

from aiogram import Bot
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession


async def notify_admins_new_inquiry(
    bot: Bot,
    inquiry,
    session: AsyncSession,
) -> None:
    """Уведомить админов о новом обращении."""
    try:
        from app.services.admin_event_monitor import (
            AdminEventMonitor,
            EventCategory,
            EventPriority,
        )

        username = "нет"
        if inquiry.user:
            username = inquiry.user.username or f"ID:{inquiry.telegram_id}"

        preview = inquiry.initial_question[:100]
        if len(inquiry.initial_question) > 100:
            preview += "..."

        monitor = AdminEventMonitor(bot, session)
        await monitor.notify(
            category=EventCategory.INQUIRY,
            priority=EventPriority.MEDIUM,
            title="Новый вопрос от пользователя",
            details={
                "ID обращения": inquiry.id,
                "Пользователь": f"@{username}",
                "Telegram ID": inquiry.telegram_id,
                "Вопрос": preview,
            },
            footer="Откройте «📨 Обращения» в админ-панели",
        )

    except Exception as e:
        logger.error(f"Ошибка уведомления админов о вопросе: {e}")
