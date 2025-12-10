"""
Admin Event Monitor - System Notifications.

This module provides notification methods for system events:
- System errors
- Maintenance mode
- Other system-level events
"""

from typing import TYPE_CHECKING

from ..constants import EventCategory, EventPriority


if TYPE_CHECKING:
    from ..monitor import AdminEventMonitor


async def notify_system_error(
    monitor: "AdminEventMonitor",
    component: str,
    error: str,
    context: str | None = None,
) -> int:
    """Уведомление о системной ошибке."""
    details = {
        "Компонент": component,
        "Ошибка": error[:200],
    }
    if context:
        details["Контекст"] = context[:100]

    return await monitor.notify(
        category=EventCategory.ERROR,
        priority=EventPriority.CRITICAL,
        title="Системная ошибка",
        details=details,
        footer="Проверьте логи для подробностей",
    )


async def notify_maintenance_mode(
    monitor: "AdminEventMonitor",
    enabled: bool,
    reason: str | None = None,
) -> int:
    """Уведомление о режиме техобслуживания."""
    status = "ВКЛЮЧЁН" if enabled else "ОТКЛЮЧЁН"
    details = {"Статус": status}
    if reason:
        details["Причина"] = reason

    return await monitor.notify(
        category=EventCategory.MAINTENANCE,
        priority=EventPriority.HIGH if enabled else EventPriority.MEDIUM,
        title=f"Режим техобслуживания {status}",
        details=details,
    )
