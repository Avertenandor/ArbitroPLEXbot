"""
AI Settings - Scheduled tasks management.
"""
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.commons import verify_admin

SCHEDULED_TASKS = [
    ("💰 Уведомления о балансе", "balance_notifications", "1 час"),
    ("💎 Мониторинг PLEX", "plex_balance_monitor", "1 час"),
    ("📈 Начисление ROI", "daily_rewards", "1 день (00:05 UTC)"),
    ("📦 Мониторинг депозитов", "deposit_monitoring", "1 минута"),
    ("⛓️ Синхронизация блокчейна", "blockchain_cache_sync", "30 секунд"),
    ("🔄 Повтор уведомлений", "notification_retry", "1 минута"),
]

VALID_TASKS = {
    "balance_notifications": "jobs.tasks.balance_notification:send_balance_notifications",
    "plex_balance_monitor": "jobs.tasks.plex_balance_monitor:monitor_plex_balances",
    "daily_rewards": "jobs.tasks.daily_rewards:process_daily_rewards",
    "deposit_monitoring": "jobs.tasks.deposit_monitoring:monitor_deposits",
    "blockchain_cache_sync": "jobs.tasks.blockchain_cache_sync:sync_blockchain_cache",
    "notification_retry": "jobs.tasks.notification_retry:retry_notifications",
}


class TasksSettingsMixin:
    """Mixin for scheduled tasks operations."""

    session: AsyncSession
    admin_telegram_id: int | None

    async def _verify_admin(self) -> tuple[Any | None, str | None]:
        return await verify_admin(self.session, self.admin_telegram_id)

    def _is_trusted_admin(self) -> bool:
        return True

    async def get_scheduled_tasks(self) -> str:
        """Get list of scheduled tasks and their status."""
        admin, error = await self._verify_admin()
        if error:
            return error

        lines = ["📋 **Запланированные задачи**\n"]
        for name, task_id, interval in SCHEDULED_TASKS:
            lines.append(f"• {name}\n  ID: `{task_id}`, Интервал: {interval}")
        lines.append(
            "\n\n💡 Для ручного запуска: `запусти задачу <task_id>`\n"
            "⚠️ Включение/отключение задач требует перезапуска сервисов"
        )
        return "\n".join(lines)

    async def trigger_task(self, task_id: str) -> str:
        """Manually trigger a scheduled task."""
        admin, error = await self._verify_admin()
        if error:
            return error
        if not self._is_trusted_admin():
            return "❌ Только доверенные админы могут запускать задачи вручную"

        if task_id not in VALID_TASKS:
            return f"❌ Неизвестная задача. Доступные: {', '.join(VALID_TASKS.keys())}"

        try:
            module_path, func_name = VALID_TASKS[task_id].rsplit(":", 1)
            logger.info(
                f"[АРЬЯ] Admin {self.admin_telegram_id} triggered task: {task_id}"
            )
            return (
                f"⚠️ Ручной запуск задачи `{task_id}` запрошен.\n\n"
                f"Для немедленного выполнения используйте:\n"
                f"`docker compose exec worker python -c "
                f"\"from {module_path} import {func_name}; "
                f"import asyncio; asyncio.run({func_name}())\"`\n\n"
                f"Или дождитесь следующего цикла по расписанию."
            )
        except Exception as e:
            logger.error(f"Error triggering task {task_id}: {e}")
            return f"❌ Ошибка: {e}"
