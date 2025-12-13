"""
AI System Administration Service - Emergency Controls.

Emergency stop controls for deposits, withdrawals, and ROI.
SECURITY: SUPER_ADMIN only for write operations.
"""
from typing import Any
from loguru import logger
from app.repositories.global_settings_repository import (
    GlobalSettingsRepository,
)


class EmergencyControlsMixin:
    """Emergency controls for AI System Service."""

    async def _check_emergency_access(
        self, require_super: bool = False
    ) -> dict[str, Any] | None:
        """Check access for emergency operations. Returns error or None."""
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        if require_super and not self._is_super_admin():
            logger.warning(
                f"AI SYSTEM SECURITY: Non-superadmin "
                f"{self.admin_telegram_id} attempted emergency operation"
            )
            return {
                "success": False,
                "error": "❌ ТОЛЬКО БОСС может управлять аварийными стопами!"
            }
        if not self._is_trusted_admin():
            return {
                "success": False,
                "error": "❌ Нет доступа к системным настройкам"
            }
        return None

    async def get_emergency_status(self) -> dict[str, Any]:
        """Get current emergency stop status."""
        if err := await self._check_emergency_access():
            return err

        repo = GlobalSettingsRepository(self.session)
        settings = await repo.get_settings()
        return {
            "success": True,
            "emergency_status": {
                "deposits_stopped": settings.emergency_stop_deposits,
                "withdrawals_stopped": (
                    settings.emergency_stop_withdrawals
                ),
                "roi_stopped": settings.emergency_stop_roi,
            },
            "status_text": (
                f"💰 Депозиты: "
                f"{'⏸ СТОП' if settings.emergency_stop_deposits else '▶️ Активны'}\n"
                f"💸 Выводы: "
                f"{'⏸ СТОП' if settings.emergency_stop_withdrawals else '▶️ Активны'}\n"
                f"📈 ROI: "
                f"{'⏸ СТОП' if settings.emergency_stop_roi else '▶️ Активны'}"
            ),
            "message": "🚨 Статус аварийных стопов"
        }

    async def toggle_emergency_deposits(
        self, enable_stop: bool
    ) -> dict[str, Any]:
        """Toggle emergency stop for deposits. SUPER_ADMIN only!"""
        if err := await self._check_emergency_access(require_super=True):
            return err

        repo = GlobalSettingsRepository(self.session)
        await repo.update_settings(emergency_stop_deposits=enable_stop)
        await self.session.commit()
        action = "ОСТАНОВЛЕНЫ" if enable_stop else "ЗАПУЩЕНЫ"
        logger.warning(
            f"AI SYSTEM: EMERGENCY - Deposits {action} "
            f"by super_admin {self.admin_telegram_id} "
            f"(@{self.admin_username})"
        )
        return {
            "success": True,
            "action": action,
            "message": f"🚨 Депозиты {action}!",
            "admin": f"@{self.admin_username}"
        }

    async def toggle_emergency_withdrawals(
        self, enable_stop: bool
    ) -> dict[str, Any]:
        """Toggle emergency stop for withdrawals. SUPER_ADMIN only!"""
        if err := await self._check_emergency_access(require_super=True):
            return err

        repo = GlobalSettingsRepository(self.session)
        await repo.update_settings(
            emergency_stop_withdrawals=enable_stop
        )
        await self.session.commit()
        action = "ОСТАНОВЛЕНЫ" if enable_stop else "ЗАПУЩЕНЫ"
        logger.warning(
            f"AI SYSTEM: EMERGENCY - Withdrawals {action} "
            f"by super_admin {self.admin_telegram_id} "
            f"(@{self.admin_username})"
        )
        return {
            "success": True,
            "action": action,
            "message": f"🚨 Выводы {action}!",
            "admin": f"@{self.admin_username}"
        }

    async def toggle_emergency_roi(
        self, enable_stop: bool
    ) -> dict[str, Any]:
        """Toggle emergency stop for ROI accruals. SUPER_ADMIN only!"""
        if err := await self._check_emergency_access(require_super=True):
            return err

        repo = GlobalSettingsRepository(self.session)
        await repo.update_settings(emergency_stop_roi=enable_stop)
        await self.session.commit()
        action = "ОСТАНОВЛЕНО" if enable_stop else "ЗАПУЩЕНО"
        logger.warning(
            f"AI SYSTEM: EMERGENCY - ROI {action} "
            f"by super_admin {self.admin_telegram_id} "
            f"(@{self.admin_username})"
        )
        return {
            "success": True,
            "action": action,
            "message": f"🚨 Начисление ROI {action}!",
            "admin": f"@{self.admin_username}"
        }

    async def emergency_full_stop(self) -> dict[str, Any]:
        """FULL EMERGENCY STOP - stops all operations. SUPER_ADMIN only!"""
        if err := await self._check_emergency_access(require_super=True):
            return err

        repo = GlobalSettingsRepository(self.session)
        await repo.update_settings(
            emergency_stop_deposits=True,
            emergency_stop_withdrawals=True,
            emergency_stop_roi=True,
        )
        await self.session.commit()
        logger.critical(
            f"AI SYSTEM: FULL EMERGENCY STOP activated "
            f"by super_admin {self.admin_telegram_id} "
            f"(@{self.admin_username})"
        )
        return {
            "success": True,
            "message": (
                "🚨🚨🚨 ПОЛНАЯ ОСТАНОВКА АКТИВИРОВАНА!\n\n"
                "❌ Депозиты: СТОП\n"
                "❌ Выводы: СТОП\n"
                "❌ ROI: СТОП"
            ),
            "admin": f"@{self.admin_username}"
        }

    async def emergency_full_resume(self) -> dict[str, Any]:
        """Resume all financial operations. SUPER_ADMIN only!"""
        if err := await self._check_emergency_access(require_super=True):
            return err

        repo = GlobalSettingsRepository(self.session)
        await repo.update_settings(
            emergency_stop_deposits=False,
            emergency_stop_withdrawals=False,
            emergency_stop_roi=False,
        )
        await self.session.commit()
        logger.warning(
            f"AI SYSTEM: All operations RESUMED "
            f"by super_admin {self.admin_telegram_id} "
            f"(@{self.admin_username})"
        )
        return {
            "success": True,
            "message": (
                "✅ ВСЕ ОПЕРАЦИИ ВОЗОБНОВЛЕНЫ!\n\n"
                "✅ Депозиты: Активны\n"
                "✅ Выводы: Активны\n"
                "✅ ROI: Активны"
            ),
            "admin": f"@{self.admin_username}"
        }
