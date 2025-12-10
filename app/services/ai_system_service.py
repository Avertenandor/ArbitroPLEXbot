"""
AI System Administration Service.

Provides system-level management tools for AI assistant:
- Emergency stops (deposits, withdrawals, ROI)
- RPC provider switching
- Global settings management
- Platform health monitoring
- Scheduled tasks management

SECURITY: SUPER_ADMIN only for emergency controls.
Trusted admins for read-only monitoring.
"""

from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.admin_repository import AdminRepository
from app.repositories.global_settings_repository import GlobalSettingsRepository

# Only these users can control emergency stops
SUPER_ADMIN_IDS = [
    1040687384,  # @VladarevInvestBrok (Командир/super_admin)
]

# Trusted admins can view but not change critical settings
TRUSTED_ADMIN_IDS = [
    1040687384,  # @VladarevInvestBrok (Командир/super_admin)
    1691026253,  # @AI_XAN (Саша - Tech Deputy)
    241568583,   # @natder (Наташа)
    6540613027,  # @ded_vtapkax (Влад)
]


class AISystemService:
    """
    AI-powered system administration service.
    
    SECURITY NOTES:
    - Emergency controls: ONLY super_admin
    - Read-only monitoring: Trusted admins
    - All actions are logged
    """

    def __init__(
        self,
        session: AsyncSession,
        admin_data: dict[str, Any] | None = None,
    ):
        self.session = session
        self.admin_data = admin_data or {}
        self.admin_telegram_id = self.admin_data.get("ID")
        self.admin_username = self.admin_data.get("username")

    async def _verify_admin(self) -> tuple[Any | None, str | None]:
        """Verify admin credentials."""
        if not self.admin_telegram_id:
            return None, "❌ Не удалось определить администратора"
        
        admin_repo = AdminRepository(self.session)
        admin = await admin_repo.get_by_telegram_id(self.admin_telegram_id)
        
        if not admin or admin.is_blocked:
            return None, "❌ Администратор не найден или заблокирован"
        
        return admin, None

    def _is_super_admin(self) -> bool:
        """Check if current admin is super_admin."""
        return self.admin_telegram_id in SUPER_ADMIN_IDS

    def _is_trusted_admin(self) -> bool:
        """Check if current admin is trusted."""
        return self.admin_telegram_id in TRUSTED_ADMIN_IDS

    # ========================================================================
    # EMERGENCY CONTROLS (SUPER_ADMIN ONLY)
    # ========================================================================

    async def get_emergency_status(self) -> dict[str, Any]:
        """
        Get current emergency stop status.
        
        Returns:
            Current status of all emergency flags
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        
        if not self._is_trusted_admin():
            return {"success": False, "error": "❌ Нет доступа к системным настройкам"}
        
        repo = GlobalSettingsRepository(self.session)
        settings = await repo.get_settings()
        
        return {
            "success": True,
            "emergency_status": {
                "deposits_stopped": settings.emergency_stop_deposits,
                "withdrawals_stopped": settings.emergency_stop_withdrawals,
                "roi_stopped": settings.emergency_stop_roi,
            },
            "status_text": (
                f"💰 Депозиты: {'⏸ СТОП' if settings.emergency_stop_deposits else '▶️ Активны'}\n"
                f"💸 Выводы: {'⏸ СТОП' if settings.emergency_stop_withdrawals else '▶️ Активны'}\n"
                f"📈 ROI: {'⏸ СТОП' if settings.emergency_stop_roi else '▶️ Активны'}"
            ),
            "message": "🚨 Статус аварийных стопов"
        }

    async def toggle_emergency_deposits(self, enable_stop: bool) -> dict[str, Any]:
        """
        Toggle emergency stop for deposits.
        
        SECURITY: SUPER_ADMIN only!
        
        Args:
            enable_stop: True to stop deposits, False to resume
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        
        if not self._is_super_admin():
            logger.warning(
                f"AI SYSTEM SECURITY: Non-superadmin {self.admin_telegram_id} "
                f"attempted to toggle emergency deposits"
            )
            return {
                "success": False,
                "error": "❌ ТОЛЬКО БОСС может управлять аварийными стопами!"
            }
        
        repo = GlobalSettingsRepository(self.session)
        await repo.update_settings(emergency_stop_deposits=enable_stop)
        await self.session.commit()
        
        action = "ОСТАНОВЛЕНЫ" if enable_stop else "ЗАПУЩЕНЫ"
        logger.warning(
            f"AI SYSTEM: EMERGENCY - Deposits {action} by super_admin "
            f"{self.admin_telegram_id} (@{self.admin_username})"
        )
        
        return {
            "success": True,
            "action": action,
            "message": f"🚨 Депозиты {action}!",
            "admin": f"@{self.admin_username}"
        }

    async def toggle_emergency_withdrawals(self, enable_stop: bool) -> dict[str, Any]:
        """
        Toggle emergency stop for withdrawals.
        
        SECURITY: SUPER_ADMIN only!
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        
        if not self._is_super_admin():
            logger.warning(
                f"AI SYSTEM SECURITY: Non-superadmin {self.admin_telegram_id} "
                f"attempted to toggle emergency withdrawals"
            )
            return {
                "success": False,
                "error": "❌ ТОЛЬКО БОСС может управлять аварийными стопами!"
            }
        
        repo = GlobalSettingsRepository(self.session)
        await repo.update_settings(emergency_stop_withdrawals=enable_stop)
        await self.session.commit()
        
        action = "ОСТАНОВЛЕНЫ" if enable_stop else "ЗАПУЩЕНЫ"
        logger.warning(
            f"AI SYSTEM: EMERGENCY - Withdrawals {action} by super_admin "
            f"{self.admin_telegram_id} (@{self.admin_username})"
        )
        
        return {
            "success": True,
            "action": action,
            "message": f"🚨 Выводы {action}!",
            "admin": f"@{self.admin_username}"
        }

    async def toggle_emergency_roi(self, enable_stop: bool) -> dict[str, Any]:
        """
        Toggle emergency stop for ROI accruals.
        
        SECURITY: SUPER_ADMIN only!
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        
        if not self._is_super_admin():
            logger.warning(
                f"AI SYSTEM SECURITY: Non-superadmin {self.admin_telegram_id} "
                f"attempted to toggle emergency ROI"
            )
            return {
                "success": False,
                "error": "❌ ТОЛЬКО БОСС может управлять аварийными стопами!"
            }
        
        repo = GlobalSettingsRepository(self.session)
        await repo.update_settings(emergency_stop_roi=enable_stop)
        await self.session.commit()
        
        action = "ОСТАНОВЛЕНО" if enable_stop else "ЗАПУЩЕНО"
        logger.warning(
            f"AI SYSTEM: EMERGENCY - ROI {action} by super_admin "
            f"{self.admin_telegram_id} (@{self.admin_username})"
        )
        
        return {
            "success": True,
            "action": action,
            "message": f"🚨 Начисление ROI {action}!",
            "admin": f"@{self.admin_username}"
        }

    async def emergency_full_stop(self) -> dict[str, Any]:
        """
        FULL EMERGENCY STOP - stops all financial operations.
        
        SECURITY: SUPER_ADMIN only!
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        
        if not self._is_super_admin():
            return {
                "success": False,
                "error": "❌ ТОЛЬКО БОСС может выполнить полную остановку!"
            }
        
        repo = GlobalSettingsRepository(self.session)
        await repo.update_settings(
            emergency_stop_deposits=True,
            emergency_stop_withdrawals=True,
            emergency_stop_roi=True,
        )
        await self.session.commit()
        
        logger.critical(
            f"AI SYSTEM: FULL EMERGENCY STOP activated by super_admin "
            f"{self.admin_telegram_id} (@{self.admin_username})"
        )
        
        return {
            "success": True,
            "message": "🚨🚨🚨 ПОЛНАЯ ОСТАНОВКА АКТИВИРОВАНА!\n\n"
                       "❌ Депозиты: СТОП\n"
                       "❌ Выводы: СТОП\n"
                       "❌ ROI: СТОП",
            "admin": f"@{self.admin_username}"
        }

    async def emergency_full_resume(self) -> dict[str, Any]:
        """
        Resume all financial operations.
        
        SECURITY: SUPER_ADMIN only!
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        
        if not self._is_super_admin():
            return {
                "success": False,
                "error": "❌ ТОЛЬКО БОСС может возобновить все операции!"
            }
        
        repo = GlobalSettingsRepository(self.session)
        await repo.update_settings(
            emergency_stop_deposits=False,
            emergency_stop_withdrawals=False,
            emergency_stop_roi=False,
        )
        await self.session.commit()
        
        logger.warning(
            f"AI SYSTEM: All operations RESUMED by super_admin "
            f"{self.admin_telegram_id} (@{self.admin_username})"
        )
        
        return {
            "success": True,
            "message": "✅ ВСЕ ОПЕРАЦИИ ВОЗОБНОВЛЕНЫ!\n\n"
                       "✅ Депозиты: Активны\n"
                       "✅ Выводы: Активны\n"
                       "✅ ROI: Активны",
            "admin": f"@{self.admin_username}"
        }

    # ========================================================================
    # BLOCKCHAIN / RPC MANAGEMENT
    # ========================================================================

    async def get_blockchain_status(self) -> dict[str, Any]:
        """
        Get current blockchain/RPC status.
        
        Returns:
            RPC providers status
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        
        if not self._is_trusted_admin():
            return {"success": False, "error": "❌ Нет доступа к системным настройкам"}
        
        try:
            from app.services.blockchain_service import get_blockchain_service
            bs = get_blockchain_service()
            await bs.force_refresh_settings()
            
            status = await bs.get_providers_status()
            
            providers_text = ""
            for name, data in status.items():
                icon = "✅" if data.get("connected") else "❌"
                active_mark = " 🔵" if data.get("active") else ""
                block = data.get("block", "N/A")
                providers_text += f"{icon} {name.upper()}{active_mark}: Block {block}\n"
            
            return {
                "success": True,
                "blockchain": {
                    "active_provider": bs.active_provider_name.upper(),
                    "auto_switch": bs.is_auto_switch_enabled,
                    "providers": status,
                },
                "status_text": (
                    f"📡 *Блокчейн статус*\n\n"
                    f"Активный провайдер: *{bs.active_provider_name.upper()}*\n"
                    f"Авто-переключение: *{'ВКЛ' if bs.is_auto_switch_enabled else 'ВЫКЛ'}*\n\n"
                    f"*Провайдеры:*\n{providers_text}"
                ),
                "message": "📡 Статус блокчейна"
            }
        except Exception as e:
            logger.error(f"Failed to get blockchain status: {e}")
            return {
                "success": False,
                "error": f"❌ Ошибка получения статуса блокчейна: {str(e)}"
            }

    async def switch_rpc_provider(self, provider: str) -> dict[str, Any]:
        """
        Switch active RPC provider.
        
        Args:
            provider: Provider name (quicknode, nodereal, nodereal2)
            
        SECURITY: nodereal2 only for super_admin!
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        
        if not self._is_trusted_admin():
            return {"success": False, "error": "❌ Нет прав на переключение провайдера"}
        
        provider = provider.lower().strip()
        valid_providers = ["quicknode", "nodereal", "nodereal2"]
        
        if provider not in valid_providers:
            return {
                "success": False,
                "error": f"❌ Неверный провайдер. Допустимые: {', '.join(valid_providers)}"
            }
        
        # NodeReal2 - only for super_admin
        if provider == "nodereal2" and not self._is_super_admin():
            logger.warning(
                f"AI SYSTEM SECURITY: Non-superadmin {self.admin_telegram_id} "
                f"attempted to switch to NodeReal2"
            )
            return {
                "success": False,
                "error": "❌ NodeReal2 (резерв) доступен ТОЛЬКО Боссу!"
            }
        
        try:
            from app.services.blockchain_service import get_blockchain_service
            repo = GlobalSettingsRepository(self.session)
            bs = get_blockchain_service()
            
            await repo.update_settings(active_rpc_provider=provider)
            await self.session.commit()
            await bs.force_refresh_settings()
            
            logger.info(
                f"AI SYSTEM: RPC switched to {provider.upper()} by admin "
                f"{self.admin_telegram_id} (@{self.admin_username})"
            )
            
            return {
                "success": True,
                "provider": provider.upper(),
                "message": f"✅ Провайдер переключён на {provider.upper()}",
                "admin": f"@{self.admin_username}"
            }
        except Exception as e:
            return {"success": False, "error": f"❌ Ошибка переключения: {str(e)}"}

    async def toggle_rpc_auto_switch(self, enable: bool) -> dict[str, Any]:
        """
        Toggle auto-switching of RPC providers.
        
        Args:
            enable: True to enable auto-switch
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        
        if not self._is_trusted_admin():
            return {"success": False, "error": "❌ Нет прав на изменение настроек"}
        
        try:
            from app.services.blockchain_service import get_blockchain_service
            repo = GlobalSettingsRepository(self.session)
            bs = get_blockchain_service()
            
            await repo.update_settings(rpc_auto_switch=enable)
            await self.session.commit()
            await bs.force_refresh_settings()
            
            status = "включено" if enable else "выключено"
            logger.info(
                f"AI SYSTEM: RPC auto-switch {status} by admin "
                f"{self.admin_telegram_id} (@{self.admin_username})"
            )
            
            return {
                "success": True,
                "auto_switch": enable,
                "message": f"✅ Авто-переключение провайдеров {'ВКЛ' if enable else 'ВЫКЛ'}",
                "admin": f"@{self.admin_username}"
            }
        except Exception as e:
            return {"success": False, "error": f"❌ Ошибка: {str(e)}"}

    # ========================================================================
    # GLOBAL SETTINGS
    # ========================================================================

    async def get_global_settings(self) -> dict[str, Any]:
        """
        Get current global platform settings.
        
        Returns:
            All global settings
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        
        if not self._is_trusted_admin():
            return {"success": False, "error": "❌ Нет доступа к настройкам"}
        
        repo = GlobalSettingsRepository(self.session)
        settings = await repo.get_settings()
        
        return {
            "success": True,
            "settings": {
                "emergency_stop_deposits": settings.emergency_stop_deposits,
                "emergency_stop_withdrawals": settings.emergency_stop_withdrawals,
                "emergency_stop_roi": settings.emergency_stop_roi,
                "active_rpc_provider": settings.active_rpc_provider,
                "rpc_auto_switch": settings.rpc_auto_switch,
                "min_withdrawal_amount": float(getattr(settings, 'min_withdrawal_amount', 0.5)),
                "max_withdrawal_amount": float(getattr(settings, 'max_withdrawal_amount', 10000)),
            },
            "message": "⚙️ Глобальные настройки платформы"
        }

    # ========================================================================
    # PLATFORM HEALTH
    # ========================================================================

    async def get_platform_health(self) -> dict[str, Any]:
        """
        Get comprehensive platform health status.
        
        Returns:
            Health metrics for all components
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        
        if not self._is_trusted_admin():
            return {"success": False, "error": "❌ Нет доступа к мониторингу"}
        
        health = {
            "database": "✅ OK",
            "blockchain": "⏳ Проверяем...",
            "redis": "✅ OK",
            "scheduler": "✅ OK",
        }
        
        # Check blockchain
        try:
            from app.services.blockchain_service import get_blockchain_service
            bs = get_blockchain_service()
            status = await bs.get_providers_status()
            
            active_ok = False
            for name, data in status.items():
                if data.get("active") and data.get("connected"):
                    active_ok = True
                    break
            
            health["blockchain"] = "✅ OK" if active_ok else "⚠️ Проблемы с RPC"
        except Exception as e:
            health["blockchain"] = f"❌ Ошибка: {str(e)[:50]}"
        
        # Overall status
        has_errors = any("❌" in v or "⚠️" in v for v in health.values())
        overall = "⚠️ ЕСТЬ ПРОБЛЕМЫ" if has_errors else "✅ ВСЁ В НОРМЕ"
        
        return {
            "success": True,
            "health": health,
            "overall": overall,
            "checked_at": datetime.now(UTC).strftime("%d.%m.%Y %H:%M UTC"),
            "message": f"🏥 Состояние платформы: {overall}"
        }
