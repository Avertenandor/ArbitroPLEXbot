"""
Admin Event Monitor - Security Notifications.

This module provides notification methods for security events:
- Security alerts
- Blacklist actions
- Suspicious activity
"""

from typing import TYPE_CHECKING

from ..constants import EventCategory, EventPriority


if TYPE_CHECKING:
    from ..monitor import AdminEventMonitor


async def notify_security_alert(
    monitor: "AdminEventMonitor",
    alert_type: str,
    user_id: int | None,
    details_text: str,
) -> int:
    """Уведомление о проблеме безопасности."""
    details = {
        "Тип угрозы": alert_type,
        "Описание": details_text[:150],
    }
    if user_id:
        details["Пользователь"] = user_id

    return await monitor.notify(
        category=EventCategory.SECURITY,
        priority=EventPriority.CRITICAL,
        title="⚠️ ПРЕДУПРЕЖДЕНИЕ БЕЗОПАСНОСТИ",
        details=details,
        footer="ТРЕБУЕТСЯ НЕМЕДЛЕННОЕ ВНИМАНИЕ!",
    )


async def notify_user_blacklisted(
    monitor: "AdminEventMonitor",
    user_id: int,
    username: str | None,
    reason: str,
    admin_id: int,
) -> int:
    """Уведомление о добавлении в чёрный список."""
    return await monitor.notify(
        category=EventCategory.BLACKLIST,
        priority=EventPriority.HIGH,
        title="Пользователь добавлен в ЧС",
        details={
            "Пользователь": f"{user_id} (@{username or 'нет'})",
            "Причина": reason[:100],
            "Добавил админ": admin_id,
        },
    )
