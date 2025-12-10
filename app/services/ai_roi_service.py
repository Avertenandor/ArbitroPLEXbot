"""
AI ROI Corridor Service.

Provides ROI corridor management for AI assistant:
- View ROI configuration by level
- Modify ROI corridors
- View corridor history

SECURITY: ROI modifications require TRUSTED_ADMIN access.
"""

from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.admin_repository import AdminRepository
from app.repositories.deposit_corridor_history_repository import (
    DepositCorridorHistoryRepository,
)
from app.repositories.global_settings_repository import GlobalSettingsRepository

# Only these admins can modify ROI
TRUSTED_ADMIN_IDS = [
    1040687384,  # @VladarevInvestBrok (Командир/super_admin)
    1691026253,  # @AI_XAN (Саша - Tech Deputy)
    241568583,   # @natder (Наташа)
    6540613027,  # @ded_vtapkax (Влад)
]


class AIRoiService:
    """
    AI-powered ROI corridor management service.
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

    def _is_trusted_admin(self) -> bool:
        """Check if current admin can modify ROI."""
        return self.admin_telegram_id in TRUSTED_ADMIN_IDS

    async def get_roi_config(self, level: int | None = None) -> dict[str, Any]:
        """
        Get ROI corridor configuration.
        
        Args:
            level: Specific level (1-5) or None for all levels
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        
        settings_repo = GlobalSettingsRepository(self.session)
        settings = await settings_repo.get_settings()
        
        levels_to_check = [level] if level else range(1, 6)
        configs = []
        
        for lvl in levels_to_check:
            if lvl < 1 or lvl > 5:
                continue
                
            roi_mode = settings.roi_settings.get(f"LEVEL_{lvl}_ROI_MODE", "custom")
            roi_min = settings.roi_settings.get(f"LEVEL_{lvl}_ROI_MIN", "0.8")
            roi_max = settings.roi_settings.get(f"LEVEL_{lvl}_ROI_MAX", "10.0")
            roi_fixed = settings.roi_settings.get(f"LEVEL_{lvl}_ROI_FIXED", "5.0")
            
            mode_desc = {
                "custom": f"Коридор {roi_min}% - {roi_max}%",
                "equal": f"Фиксированный {roi_fixed}%",
            }.get(roi_mode, roi_mode)
            
            configs.append({
                "level": lvl,
                "mode": roi_mode,
                "mode_description": mode_desc,
                "roi_min": float(roi_min),
                "roi_max": float(roi_max),
                "roi_fixed": float(roi_fixed),
            })
        
        return {
            "success": True,
            "configs": configs,
            "message": f"📊 ROI конфигурация" + (f" уровня {level}" if level else " всех уровней")
        }

    async def set_roi_corridor(
        self,
        level: int,
        mode: str,
        roi_min: float | None = None,
        roi_max: float | None = None,
        roi_fixed: float | None = None,
        reason: str = "",
    ) -> dict[str, Any]:
        """
        Set ROI corridor for a level.
        
        SECURITY: TRUSTED ADMIN only!
        
        Args:
            level: Deposit level (1-5)
            mode: "custom" (min-max range) or "equal" (fixed rate)
            roi_min: Minimum ROI % (for custom mode)
            roi_max: Maximum ROI % (for custom mode)
            roi_fixed: Fixed ROI % (for equal mode)
            reason: Reason for change
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        
        if not self._is_trusted_admin():
            logger.warning(
                f"AI ROI SECURITY: Untrusted admin {self.admin_telegram_id} "
                f"attempted to modify ROI corridor"
            )
            return {"success": False, "error": "❌ Нет прав на изменение ROI коридора"}
        
        if level < 1 or level > 5:
            return {"success": False, "error": "❌ Уровень должен быть от 1 до 5"}
        
        if mode not in ["custom", "equal"]:
            return {"success": False, "error": "❌ Режим должен быть 'custom' или 'equal'"}
        
        if mode == "custom":
            if roi_min is None or roi_max is None:
                return {"success": False, "error": "❌ Для режима custom укажите roi_min и roi_max"}
            if roi_min < 0 or roi_max < 0:
                return {"success": False, "error": "❌ ROI не может быть отрицательным"}
            if roi_min >= roi_max:
                return {"success": False, "error": "❌ roi_min должен быть меньше roi_max"}
        
        if mode == "equal":
            if roi_fixed is None:
                return {"success": False, "error": "❌ Для режима equal укажите roi_fixed"}
            if roi_fixed < 0:
                return {"success": False, "error": "❌ ROI не может быть отрицательным"}
        
        settings_repo = GlobalSettingsRepository(self.session)
        settings = await settings_repo.get_settings()
        
        # Save old values for logging
        old_mode = settings.roi_settings.get(f"LEVEL_{level}_ROI_MODE", "custom")
        old_min = settings.roi_settings.get(f"LEVEL_{level}_ROI_MIN", "0.8")
        old_max = settings.roi_settings.get(f"LEVEL_{level}_ROI_MAX", "10.0")
        
        # Update settings
        new_roi_settings = dict(settings.roi_settings)
        new_roi_settings[f"LEVEL_{level}_ROI_MODE"] = mode
        
        if mode == "custom":
            new_roi_settings[f"LEVEL_{level}_ROI_MIN"] = str(roi_min)
            new_roi_settings[f"LEVEL_{level}_ROI_MAX"] = str(roi_max)
        elif mode == "equal":
            new_roi_settings[f"LEVEL_{level}_ROI_FIXED"] = str(roi_fixed)
        
        await settings_repo.update_settings(roi_settings=new_roi_settings)
        
        # Log to corridor history
        try:
            history_repo = DepositCorridorHistoryRepository(self.session)
            await history_repo.create(
                deposit_level=level,
                roi_min=Decimal(str(roi_min)) if roi_min else Decimal(old_min),
                roi_max=Decimal(str(roi_max)) if roi_max else Decimal(old_max),
                changed_by_admin_id=admin.id if admin else None,
                reason=f"[АРЬЯ] {reason}" if reason else "[АРЬЯ] Изменение через AI",
            )
        except Exception as e:
            logger.warning(f"Failed to log corridor history: {e}")
        
        await self.session.commit()
        
        logger.info(
            f"AI ROI: Admin {self.admin_telegram_id} changed level {level} ROI: "
            f"mode {old_mode} → {mode}, min {old_min} → {roi_min}, max {old_max} → {roi_max}. "
            f"Reason: {reason}"
        )
        
        return {
            "success": True,
            "level": level,
            "old": {"mode": old_mode, "min": float(old_min), "max": float(old_max)},
            "new": {
                "mode": mode,
                "min": roi_min,
                "max": roi_max,
                "fixed": roi_fixed,
            },
            "reason": reason,
            "admin": f"@{self.admin_username}",
            "message": f"✅ ROI коридор уровня {level} изменён"
        }

    async def get_corridor_history(
        self,
        level: int | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Get ROI corridor change history.
        
        Args:
            level: Specific level or None for all
            limit: Max results
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        
        history_repo = DepositCorridorHistoryRepository(self.session)
        
        # Get history entries
        from app.models.deposit_corridor_history import DepositCorridorHistory
        
        stmt = select(DepositCorridorHistory).order_by(
            DepositCorridorHistory.created_at.desc()
        ).limit(limit)
        
        if level:
            stmt = stmt.where(DepositCorridorHistory.deposit_level == level)
        
        result = await self.session.execute(stmt)
        entries = list(result.scalars().all())
        
        if not entries:
            return {
                "success": True,
                "history": [],
                "message": "ℹ️ История изменений пуста"
            }
        
        history_list = []
        for entry in entries:
            history_list.append({
                "id": entry.id,
                "level": entry.deposit_level,
                "roi_min": float(entry.roi_min),
                "roi_max": float(entry.roi_max),
                "reason": entry.reason,
                "created": entry.created_at.strftime("%d.%m.%Y %H:%M") if entry.created_at else None,
            })
        
        return {
            "success": True,
            "count": len(history_list),
            "history": history_list,
            "message": f"📜 История изменений ROI" + (f" уровня {level}" if level else "")
        }
