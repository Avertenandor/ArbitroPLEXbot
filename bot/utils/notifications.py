"""
Notification utilities.

Helper functions for sending notifications.
Включает интеграцию с AdminEventMonitor для структурированных уведомлений.
"""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from aiogram import Bot
from loguru import logger

from app.config.constants import TELEGRAM_TIMEOUT

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def notify_admins(
    bot: Bot,
    admin_ids: list[int],
    message: str,
    parse_mode: str = "Markdown",
) -> int:
    """
    Отправить уведомление всем админам параллельно.

    Args:
        bot: Экземпляр бота
        admin_ids: Список Telegram ID админов
        message: Текст сообщения
        parse_mode: Режим парсинга (Markdown, HTML)

    Returns:
        Количество успешно уведомлённых админов
    """
    if not admin_ids:
        logger.warning("Не указаны ID админов для уведомления")
        return 0

    async def send_to_admin(admin_id: int) -> tuple[int, bool]:
        """Отправить сообщение одному админу."""
        try:
            await asyncio.wait_for(
                bot.send_message(
                    admin_id,
                    message,
                    parse_mode=parse_mode,
                ),
                timeout=TELEGRAM_TIMEOUT,
            )
            return admin_id, True
        except TimeoutError:
            logger.error(f"Таймаут уведомления админа {admin_id}")
            return admin_id, False
        except Exception as e:
            logger.error(f"Ошибка уведомления админа {admin_id}: {e}")
            return admin_id, False

    # Параллельная отправка
    tasks = [send_to_admin(admin_id) for admin_id in admin_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Подсчёт неудач
    success_count = 0
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Задача уведомления завершилась с ошибкой: {result}")
        else:
            _, success = result
            if success:
                success_count += 1

    if success_count < len(admin_ids):
        logger.warning(
            f"Уведомлено {success_count}/{len(admin_ids)} админов"
        )
    else:
        logger.debug(f"Все {len(admin_ids)} админов успешно уведомлены")

    return success_count


async def notify_admins_formatted(
    bot: Bot,
    session: "AsyncSession",
    title: str,
    details: dict[str, Any],
    category: str = "system",
    priority: str = "medium",
    footer: str | None = None,
) -> int:
    """
    Отправить форматированное уведомление через AdminEventMonitor.

    Args:
        bot: Экземпляр бота
        session: Сессия БД
        title: Заголовок
        details: Детали события
        category: Категория (deposit, withdrawal, security, etc.)
        priority: Приоритет (critical, high, medium, low)
        footer: Дополнительный текст

    Returns:
        Количество уведомлённых админов
    """
    from app.services.admin_event_monitor import (
        AdminEventMonitor,
        EventCategory,
        EventPriority,
    )

    # Преобразование строк в enum
    try:
        cat = EventCategory(category)
    except ValueError:
        cat = EventCategory.SYSTEM

    try:
        prio = EventPriority(priority)
    except ValueError:
        prio = EventPriority.MEDIUM

    monitor = AdminEventMonitor(bot, session)
    return await monitor.notify(
        category=cat,
        priority=prio,
        title=title,
        details=details,
        footer=footer,
    )


def format_admin_alert(
    title: str,
    details: dict[str, Any],
    priority: str = "medium",
    category: str | None = None,
) -> str:
    """
    Форматировать сообщение для админов в едином стиле.

    Args:
        title: Заголовок
        details: Детали (ключ-значение)
        priority: Приоритет (critical, high, medium, low)
        category: Категория события

    Returns:
        Отформатированное сообщение
    """
    # Эмодзи приоритетов
    priority_emoji = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🟢",
    }

    priority_names = {
        "critical": "КРИТИЧЕСКИЙ",
        "high": "Высокий",
        "medium": "Средний",
        "low": "Низкий",
    }

    prio_emoji = priority_emoji.get(priority, "⚪")
    prio_name = priority_names.get(priority, priority)

    lines = [
        f"*{title}*",
        f"{prio_emoji} Приоритет: {prio_name}",
    ]

    if category:
        lines.append(f"📂 Категория: {category}")

    lines.append("")

    # Детали
    for key, value in details.items():
        if value is not None:
            # Форматирование
            if isinstance(value, Decimal):
                value = f"{value:,.4f}".rstrip("0").rstrip(".")
            elif isinstance(value, datetime):
                value = value.strftime("%d.%m.%Y %H:%M:%S")
            elif isinstance(value, bool):
                value = "Да" if value else "Нет"

            lines.append(f"• {key}: `{value}`")

    # Время
    lines.append("")
    lines.append(f"🕐 {datetime.now(UTC).strftime('%d.%m.%Y %H:%M:%S')} UTC")

    return "\n".join(lines)
