"""
Admin Event Monitor - User Notifications.

This module provides notification methods for user-related events:
- Registration
- Verification
- Account recovery
"""

from typing import TYPE_CHECKING

from ..constants import EventCategory, EventPriority

if TYPE_CHECKING:
    from ..monitor import AdminEventMonitor


async def notify_new_registration(
    monitor: "AdminEventMonitor",
    user_id: int,
    username: str | None,
    telegram_id: int,
    referrer_id: int | None = None,
) -> int:
    """Уведомление о регистрации пользователя."""
    details = {
        "ID пользователя": user_id,
        "Username": f"@{username}" if username else "нет",
        "Telegram ID": telegram_id,
    }
    if referrer_id:
        details["Пригласил"] = f"ID: {referrer_id}"

    return await monitor.notify(
        category=EventCategory.USER_REGISTRATION,
        priority=EventPriority.LOW,
        title="Новая регистрация",
        details=details,
    )


async def notify_finpass_recovery(
    monitor: "AdminEventMonitor",
    user_id: int,
    username: str | None,
    method: str,
) -> int:
    """Уведомление о запросе восстановления фин. пароля."""
    return await monitor.notify(
        category=EventCategory.USER_RECOVERY,
        priority=EventPriority.HIGH,
        title="Запрос восстановления фин. пароля",
        details={
            "Пользователь": f"{user_id} (@{username or 'нет'})",
            "Метод": method,
        },
        footer="Проверьте подлинность запроса",
    )
