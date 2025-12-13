"""
AI Settings Service.

Provides platform settings management for AI assistant:
- Withdrawal settings (min amount, limits, auto-withdrawal, fees)
- Deposit settings (level corridors, enable/disable levels, PLEX rate)
- Scheduled tasks management
- Admin management

SECURITY:
- Read-only for all admins
- Write operations only for trusted admins
"""
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

try:
    from redis.asyncio import Redis as AsyncRedis
except ImportError:
    import redis.asyncio as aioredis
    AsyncRedis = aioredis.Redis

from .admin_ops import AdminOpsMixin
from .deposit import DepositSettingsMixin
from .tasks import TasksSettingsMixin
from .withdrawal import WithdrawalSettingsMixin


class AISettingsService(
    WithdrawalSettingsMixin,
    DepositSettingsMixin,
    TasksSettingsMixin,
    AdminOpsMixin,
):
    """
    AI-powered settings management service.

    Provides withdrawal and deposit settings management for ARIA.
    Uses mixin pattern for modular organization.
    """

    def __init__(
        self,
        session: AsyncSession,
        admin_data: dict[str, Any] | None = None,
        redis_client: AsyncRedis | None = None,
    ):
        self.session = session
        self.admin_data = admin_data or {}
        self.admin_telegram_id = self.admin_data.get("ID")
        self.admin_username = self.admin_data.get("username")
        self.redis_client = redis_client


__all__ = ['AISettingsService']
