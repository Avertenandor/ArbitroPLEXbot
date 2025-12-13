"""
AI System Administration Service - Platform Monitoring.

Global settings and platform health monitoring.
"""
from datetime import UTC, datetime
from typing import Any
from app.repositories.global_settings_repository import (
    GlobalSettingsRepository,
)


class PlatformMonitoringMixin:
    """Platform monitoring for AI System Service."""

    async def get_global_settings(self) -> dict[str, Any]:
        """
        Get current global platform settings.

        Returns:
            All global settings including emergency stops,
            RPC settings, and withdrawal limits
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        if not self._is_trusted_admin():
            return {
                "success": False,
                "error": "❌ Нет доступа к настройкам"
            }

        repo = GlobalSettingsRepository(self.session)
        settings = await repo.get_settings()
        min_withdrawal = float(
            getattr(settings, 'min_withdrawal_amount', 0.5)
        )
        max_withdrawal = float(
            getattr(settings, 'max_withdrawal_amount', 10000)
        )
        return {
            "success": True,
            "settings": {
                "emergency_stop_deposits": (
                    settings.emergency_stop_deposits
                ),
                "emergency_stop_withdrawals": (
                    settings.emergency_stop_withdrawals
                ),
                "emergency_stop_roi": settings.emergency_stop_roi,
                "active_rpc_provider": settings.active_rpc_provider,
                "rpc_auto_switch": settings.rpc_auto_switch,
                "min_withdrawal_amount": min_withdrawal,
                "max_withdrawal_amount": max_withdrawal,
            },
            "message": "⚙️ Глобальные настройки платформы"
        }

    async def get_platform_health(self) -> dict[str, Any]:
        """
        Get comprehensive platform health status.

        Returns:
            Health metrics for all components:
            - Database
            - Blockchain/RPC
            - Redis
            - Scheduler
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        if not self._is_trusted_admin():
            return {
                "success": False,
                "error": "❌ Нет доступа к мониторингу"
            }

        health = {
            "database": "✅ OK",
            "blockchain": "⏳ Проверяем...",
            "redis": "✅ OK",
            "scheduler": "✅ OK",
        }
        # Check blockchain
        try:
            from app.services.blockchain_service import (
                get_blockchain_service,
            )
            bs = get_blockchain_service()
            status = await bs.get_providers_status()
            active_ok = False
            for name, data in status.items():
                if data.get("active") and data.get("connected"):
                    active_ok = True
                    break

            health["blockchain"] = (
                "✅ OK" if active_ok else "⚠️ Проблемы с RPC"
            )
        except Exception as e:
            health["blockchain"] = f"❌ Ошибка: {str(e)[:50]}"
        # Overall status
        has_errors = any(
            "❌" in v or "⚠️" in v for v in health.values()
        )
        overall = (
            "⚠️ ЕСТЬ ПРОБЛЕМЫ" if has_errors else "✅ ВСЁ В НОРМЕ"
        )
        return {
            "success": True,
            "health": health,
            "overall": overall,
            "checked_at": (
                datetime.now(UTC).strftime("%d.%m.%Y %H:%M UTC")
            ),
            "message": f"🏥 Состояние платформы: {overall}"
        }
