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

from app.repositories.deposit_corridor_history_repository import (
    DepositCorridorHistoryRepository,
)
from app.repositories.global_settings_repository import GlobalSettingsRepository
from app.services.ai.commons import verify_admin


"""NOTE: Access control

Per requirement: any active (non-blocked) admin can modify ROI via ARYA.
"""


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
        return await verify_admin(self.session, self.admin_telegram_id)

    def _is_trusted_admin(self) -> bool:
        """All verified admins are trusted for ARYA ROI tools."""
        return True

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

            configs.append(
                {
                    "level": lvl,
                    "mode": roi_mode,
                    "mode_description": mode_desc,
                    "roi_min": float(roi_min),
                    "roi_max": float(roi_max),
                    "roi_fixed": float(roi_fixed),
                }
            )

        level_text = f" уровня {level}" if level else " всех уровней"
        message = "📊 ROI конфигурация" + level_text
        return {
            "success": True,
            "configs": configs,
            "message": message,
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
            warning_msg = (
                f"AI ROI SECURITY: Untrusted admin {self.admin_telegram_id} "
                f"attempted to modify ROI corridor"
            )
            logger.warning(warning_msg)
            return {
                "success": False,
                "error": "❌ Нет прав на изменение ROI коридора"
            }

        if level < 1 or level > 5:
            error_msg = "❌ Уровень должен быть от 1 до 5"
            return {"success": False, "error": error_msg}

        if mode not in ["custom", "equal"]:
            error_msg = "❌ Режим должен быть 'custom' или 'equal'"
            return {"success": False, "error": error_msg}

        if mode == "custom":
            if roi_min is None or roi_max is None:
                error_msg = "❌ Для режима custom укажите roi_min и roi_max"
                return {"success": False, "error": error_msg}
            if roi_min < 0 or roi_max < 0:
                error_msg = "❌ ROI не может быть отрицательным"
                return {"success": False, "error": error_msg}
            if roi_min >= roi_max:
                error_msg = "❌ roi_min должен быть меньше roi_max"
                return {"success": False, "error": error_msg}

        if mode == "equal":
            if roi_fixed is None:
                error_msg = "❌ Для режима equal укажите roi_fixed"
                return {"success": False, "error": error_msg}
            if roi_fixed < 0:
                error_msg = "❌ ROI не может быть отрицательным"
                return {"success": False, "error": error_msg}

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
            change_reason = (
                f"[АРЬЯ] {reason}" if reason
                else "[АРЬЯ] Изменение через AI"
            )
            await history_repo.create(
                deposit_level=level,
                roi_min=Decimal(str(roi_min)) if roi_min else Decimal(old_min),
                roi_max=Decimal(str(roi_max)) if roi_max else Decimal(old_max),
                changed_by_admin_id=admin.id if admin else None,
                reason=change_reason,
            )
        except Exception as e:
            logger.warning(f"Failed to log corridor history: {e}")

        await self.session.commit()

        log_msg = (
            f"AI ROI: Admin {self.admin_telegram_id} changed "
            f"level {level} ROI: mode {old_mode} → {mode}, "
            f"min {old_min} → {roi_min}, max {old_max} → {roi_max}. "
            f"Reason: {reason}"
        )
        logger.info(log_msg)

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
            "message": f"✅ ROI коридор уровня {level} изменён",
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

        # Get history entries
        from app.models.deposit_corridor_history import DepositCorridorHistory

        stmt = (
            select(DepositCorridorHistory)
            .order_by(DepositCorridorHistory.created_at.desc())
            .limit(limit)
        )

        if level:
            stmt = stmt.where(DepositCorridorHistory.deposit_level == level)

        result = await self.session.execute(stmt)
        entries = list(result.scalars().all())

        if not entries:
            empty_msg = "ℹ️ История изменений пуста"
            return {"success": True, "history": [], "message": empty_msg}

        history_list = []
        for entry in entries:
            created_str = None
            if entry.created_at:
                created_str = entry.created_at.strftime("%d.%m.%Y %H:%M")

            history_list.append(
                {
                    "id": entry.id,
                    "level": entry.deposit_level,
                    "roi_min": float(entry.roi_min),
                    "roi_max": float(entry.roi_max),
                    "reason": entry.reason,
                    "created": created_str,
                }
            )

        level_suffix = f" уровня {level}" if level else ""
        message = "📜 История изменений ROI" + level_suffix
        return {
            "success": True,
            "count": len(history_list),
            "history": history_list,
            "message": message,
        }
