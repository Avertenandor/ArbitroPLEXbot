"""
AI System Administration Service - RPC Management.

Blockchain RPC provider management and switching.
"""
from typing import Any
from loguru import logger
from app.repositories.global_settings_repository import (
    GlobalSettingsRepository,
)


class RPCManagementMixin:
    """RPC provider management for AI System Service."""

    async def _check_rpc_access(self) -> dict[str, Any] | None:
        """Check access for RPC operations. Returns error or None."""
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        if not self._is_trusted_admin():
            return {
                "success": False,
                "error": "❌ Нет доступа к системным настройкам"
            }
        return None

    async def get_blockchain_status(self) -> dict[str, Any]:
        """Get current blockchain/RPC status."""
        if err := await self._check_rpc_access():
            return err

        try:
            from app.services.blockchain_service import (
                get_blockchain_service,
            )
            bs = get_blockchain_service()
            await bs.force_refresh_settings()
            status = await bs.get_providers_status()
            providers_text = ""
            for name, data in status.items():
                icon = "✅" if data.get("connected") else "❌"
                active_mark = " 🔵" if data.get("active") else ""
                block = data.get("block", "N/A")
                providers_text += (
                    f"{icon} {name.upper()}{active_mark}: "
                    f"Block {block}\n"
                )
            return {
                "success": True,
                "blockchain": {
                    "active_provider": (
                        bs.active_provider_name.upper()
                    ),
                    "auto_switch": bs.is_auto_switch_enabled,
                    "providers": status,
                },
                "status_text": (
                    f"📡 *Блокчейн статус*\n\n"
                    f"Активный провайдер: "
                    f"*{bs.active_provider_name.upper()}*\n"
                    f"Авто-переключение: "
                    f"*{'ВКЛ' if bs.is_auto_switch_enabled else 'ВЫКЛ'}*\n\n"
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

    async def switch_rpc_provider(
        self, provider: str
    ) -> dict[str, Any]:
        """Switch active RPC provider. nodereal2 - SUPER_ADMIN only!"""
        if err := await self._check_rpc_access():
            return err

        provider = provider.lower().strip()
        valid_providers = ["quicknode", "nodereal", "nodereal2"]

        if provider not in valid_providers:
            return {
                "success": False,
                "error": (
                    f"❌ Неверный провайдер. "
                    f"Допустимые: {', '.join(valid_providers)}"
                )
            }
        # NodeReal2 - only for super_admin
        if provider == "nodereal2" and not self._is_super_admin():
            logger.warning(
                f"AI SYSTEM SECURITY: Non-superadmin "
                f"{self.admin_telegram_id} "
                f"attempted to switch to NodeReal2"
            )
            return {
                "success": False,
                "error": "❌ NodeReal2 (резерв) доступен ТОЛЬКО Боссу!"
            }

        try:
            from app.services.blockchain_service import (
                get_blockchain_service,
            )
            repo = GlobalSettingsRepository(self.session)
            bs = get_blockchain_service()
            await repo.update_settings(active_rpc_provider=provider)
            await self.session.commit()
            await bs.force_refresh_settings()
            logger.info(
                f"AI SYSTEM: RPC switched to {provider.upper()} "
                f"by admin {self.admin_telegram_id} "
                f"(@{self.admin_username})"
            )
            return {
                "success": True,
                "provider": provider.upper(),
                "message": f"✅ Провайдер переключён на {provider.upper()}",
                "admin": f"@{self.admin_username}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"❌ Ошибка переключения: {str(e)}"
            }

    async def toggle_rpc_auto_switch(
        self, enable: bool
    ) -> dict[str, Any]:
        """Toggle auto-switching of RPC providers."""
        if err := await self._check_rpc_access():
            return err

        try:
            from app.services.blockchain_service import (
                get_blockchain_service,
            )
            repo = GlobalSettingsRepository(self.session)
            bs = get_blockchain_service()
            await repo.update_settings(rpc_auto_switch=enable)
            await self.session.commit()
            await bs.force_refresh_settings()
            status = "включено" if enable else "выключено"
            logger.info(
                f"AI SYSTEM: RPC auto-switch {status} "
                f"by admin {self.admin_telegram_id} "
                f"(@{self.admin_username})"
            )
            status_text = 'ВКЛ' if enable else 'ВЫКЛ'
            return {
                "success": True,
                "auto_switch": enable,
                "message": (
                    f"✅ Авто-переключение провайдеров {status_text}"
                ),
                "admin": f"@{self.admin_username}"
            }
        except Exception as e:
            return {"success": False, "error": f"❌ Ошибка: {str(e)}"}
