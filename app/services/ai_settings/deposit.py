"""
AI Settings - Deposit settings management.
"""
from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.deposit_level_config_repository import (
    DepositLevelConfigRepository,
)
from app.services.ai.commons import verify_admin

VALID_LEVELS = ["test", "level_1", "level_2", "level_3", "level_4", "level_5"]
LEVEL_EMOJI = {
    "test": "🎯", "level_1": "💰", "level_2": "💎",
    "level_3": "🏆", "level_4": "👑", "level_5": "🚀",
}


class DepositSettingsMixin:
    """Mixin for deposit settings operations."""

    session: AsyncSession
    admin_telegram_id: int | None

    async def _verify_admin(self) -> tuple[Any | None, str | None]:
        return await verify_admin(self.session, self.admin_telegram_id)

    def _is_trusted_admin(self) -> bool:
        return True

    async def get_deposit_settings(self) -> str:
        """Get current deposit level settings."""
        admin, error = await self._verify_admin()
        if error:
            return error

        try:
            config_repo = DepositLevelConfigRepository(self.session)
            levels = await config_repo.get_all_ordered()
            if not levels:
                return "⚠️ Уровни депозитов не настроены"

            lines = ["⚙️ **Настройки уровней депозитов**\n"]
            plex_rate = None

            for lc in levels:
                emoji = LEVEL_EMOJI.get(lc.level_type, "📊")
                status = "✅" if lc.is_active else "❌"
                lines.append(
                    f"{emoji} {lc.name}: "
                    f"${lc.min_amount:,.0f} - ${lc.max_amount:,.0f} {status}"
                )
                if plex_rate is None:
                    plex_rate = lc.plex_per_dollar

            lines.append(f"\n💎 PLEX за $1: {plex_rate} токенов")
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Error getting deposit settings: {e}")
            return f"❌ Ошибка: {e}"

    async def set_level_corridor(
        self, level_type: str, min_amount: Decimal, max_amount: Decimal
    ) -> str:
        """Set min/max deposit amount for a level."""
        admin, error = await self._verify_admin()
        if error:
            return error
        if not self._is_trusted_admin():
            return "❌ Только доверенные админы могут изменять настройки депозитов"

        if level_type not in VALID_LEVELS:
            return f"❌ Неверный уровень. Доступные: {', '.join(VALID_LEVELS)}"

        if min_amount >= max_amount:
            return "❌ Минимум должен быть меньше максимума"
        if min_amount < Decimal("1"):
            return "❌ Минимальная сумма не может быть меньше 1 USDT"

        try:
            config_repo = DepositLevelConfigRepository(self.session)
            level_config = await config_repo.get_by_level_type(level_type)
            if not level_config:
                return f"❌ Уровень {level_type} не найден"

            level_config.min_amount = min_amount
            level_config.max_amount = max_amount
            self.session.add(level_config)
            await self.session.commit()
            logger.info(
                f"[АРЬЯ] Admin {self.admin_telegram_id} set {level_type} "
                f"corridor: ${min_amount}-${max_amount}"
            )
            return (
                f"✅ Коридор уровня `{level_type}` изменён:\n"
                f"Минимум: `${min_amount:,.0f}`\n"
                f"Максимум: `${max_amount:,.0f}`"
            )
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error setting level corridor: {e}")
            return f"❌ Ошибка: {e}"

    async def toggle_deposit_level(self, level_type: str, enabled: bool) -> str:
        """Enable or disable a deposit level."""
        admin, error = await self._verify_admin()
        if error:
            return error
        if not self._is_trusted_admin():
            return "❌ Только доверенные админы могут изменять настройки депозитов"

        if level_type not in VALID_LEVELS:
            return f"❌ Неверный уровень. Доступные: {', '.join(VALID_LEVELS)}"

        try:
            config_repo = DepositLevelConfigRepository(self.session)
            level_config = await config_repo.get_by_level_type(level_type)
            if not level_config:
                return f"❌ Уровень {level_type} не найден"

            level_config.is_active = enabled
            self.session.add(level_config)
            await self.session.commit()
            status = "включен" if enabled else "отключен"
            logger.info(
                f"[АРЬЯ] Admin {self.admin_telegram_id} toggled {level_type}: {status}"
            )
            return f"✅ Уровень `{level_type}` {status}"
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error toggling deposit level: {e}")
            return f"❌ Ошибка: {e}"

    async def set_plex_rate(self, rate: Decimal) -> str:
        """Set PLEX tokens required per dollar of deposit."""
        admin, error = await self._verify_admin()
        if error:
            return error
        if not self._is_trusted_admin():
            return "❌ Только доверенные админы могут изменять настройки депозитов"

        if rate < Decimal("1") or rate > Decimal("100"):
            return "❌ PLEX rate должен быть от 1 до 100"

        try:
            config_repo = DepositLevelConfigRepository(self.session)
            levels = await config_repo.get_all_ordered()
            for level_config in levels:
                level_config.plex_per_dollar = rate
                self.session.add(level_config)
            await self.session.commit()
            logger.info(
                f"[АРЬЯ] Admin {self.admin_telegram_id} set PLEX rate to {rate}"
            )
            return f"✅ PLEX за $1 установлен: `{rate}` токенов для всех уровней"
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error setting PLEX rate: {e}")
            return f"❌ Ошибка: {e}"
