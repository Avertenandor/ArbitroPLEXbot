"""
Admin Event Monitor - Core Monitoring Class.

This module contains the core AdminEventMonitor class that handles
admin notifications and event tracking.
"""

import asyncio
from typing import TYPE_CHECKING, Any

from loguru import logger

from app.config.constants import TELEGRAM_TIMEOUT

from .constants import EventCategory, EventPriority
from .formatter import format_admin_message

if TYPE_CHECKING:
    from aiogram import Bot
    from sqlalchemy.ext.asyncio import AsyncSession


class AdminEventMonitor:
    """
    Сервис мониторинга событий для администраторов.

    Обеспечивает:
    - Категоризацию событий
    - Приоритизацию уведомлений
    - Форматирование сообщений на русском языке
    - Параллельную отправку всем админам
    """

    def __init__(
        self,
        bot: "Bot",
        session: "AsyncSession",
    ) -> None:
        """
        Инициализация монитора.

        Args:
            bot: Экземпляр бота
            session: Сессия базы данных
        """
        self.bot = bot
        self.session = session

    async def _get_admin_ids(self) -> list[int]:
        """Получить список Telegram ID всех активных админов."""
        from app.repositories.admin_repository import AdminRepository

        admin_repo = AdminRepository(self.session)
        admins = await admin_repo.find_by(is_blocked=False)
        return [admin.telegram_id for admin in admins if admin.telegram_id]

    async def _send_to_admins(
        self,
        message: str,
        priority: EventPriority,
    ) -> int:
        """
        Отправить сообщение всем админам.

        Args:
            message: Текст сообщения
            priority: Приоритет (для логирования)

        Returns:
            Количество успешно уведомлённых админов
        """
        admin_ids = await self._get_admin_ids()

        if not admin_ids:
            logger.warning("Нет активных админов для уведомления")
            return 0

        async def send_to_admin(admin_id: int) -> bool:
            try:
                await asyncio.wait_for(
                    self.bot.send_message(
                        chat_id=admin_id,
                        text=message,
                        parse_mode="Markdown",
                    ),
                    timeout=TELEGRAM_TIMEOUT,
                )
                return True
            except TimeoutError:
                logger.warning(f"Таймаут отправки админу {admin_id}")
                return False
            except Exception as e:
                logger.error(f"Ошибка отправки админу {admin_id}: {e}")
                return False

        # Параллельная отправка
        tasks = [send_to_admin(admin_id) for admin_id in admin_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(
            1 for r in results
            if r is True
        )

        if success_count < len(admin_ids):
            logger.warning(
                f"Уведомлено {success_count}/{len(admin_ids)} админов "
                f"(приоритет: {priority.value})"
            )
        else:
            logger.debug(f"Все {success_count} админов уведомлены")

        return success_count

    async def notify(
        self,
        category: EventCategory,
        priority: EventPriority,
        title: str,
        details: dict[str, Any],
        footer: str | None = None,
    ) -> int:
        """
        Отправить уведомление о событии.

        Args:
            category: Категория события
            priority: Приоритет
            title: Заголовок
            details: Детали события
            footer: Дополнительный текст

        Returns:
            Количество уведомлённых админов
        """
        message = format_admin_message(
            category, priority, title, details, footer
        )
        return await self._send_to_admins(message, priority)


async def get_admin_monitor(
    bot: "Bot",
    session: "AsyncSession",
) -> AdminEventMonitor:
    """
    Получить экземпляр монитора событий.

    Args:
        bot: Экземпляр бота
        session: Сессия БД

    Returns:
        AdminEventMonitor
    """
    return AdminEventMonitor(bot, session)
