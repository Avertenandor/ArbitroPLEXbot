"""
AI Settings - Withdrawal settings management.
"""
from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.global_settings_repository import GlobalSettingsRepository
from app.services.ai.commons import verify_admin


class WithdrawalSettingsMixin:
    """Mixin for withdrawal settings operations."""

    session: AsyncSession
    admin_telegram_id: int | None
    redis_client: Any

    async def _verify_admin(self) -> tuple[Any | None, str | None]:
        return await verify_admin(self.session, self.admin_telegram_id)

    def _is_trusted_admin(self) -> bool:
        return True

    async def get_withdrawal_settings(self) -> str:
        """Get current withdrawal settings."""
        admin, error = await self._verify_admin()
        if error:
            return error

        try:
            repo = GlobalSettingsRepository(self.session)
            settings = await repo.get_settings()
            limit_status = (
                "✅ Включено" if settings.is_daily_limit_enabled else "❌ Выключено"
            )
            auto_status = (
                "✅ Включен" if settings.auto_withdrawal_enabled else "❌ Выключен"
            )
            limit_val = (
                f"{settings.daily_withdrawal_limit} USDT"
                if settings.daily_withdrawal_limit
                else "Не задан"
            )
            service_fee = getattr(settings, "withdrawal_service_fee", Decimal("0.00"))
            return (
                f"⚙️ **Настройки выводов**\n\n"
                f"💵 Мин. вывод: `{settings.min_withdrawal_amount} USDT`\n"
                f"🛡 Дневной лимит: `{limit_val}`\n"
                f"🔒 Ограничение лимита: {limit_status}\n"
                f"⚡️ Авто-вывод: {auto_status}\n"
                f"💸 Комиссия сервиса: `{service_fee}%`\n\n"
                f"_Авто-вывод работает по правилу x5 "
                f"(Депозиты * 5 >= Выводы + Запрос)._"
            )
        except Exception as e:
            logger.error(f"Error getting withdrawal settings: {e}")
            return f"❌ Ошибка: {e}"

    async def set_min_withdrawal(self, amount: Decimal) -> str:
        """Set minimum withdrawal amount."""
        admin, error = await self._verify_admin()
        if error:
            return error
        if not self._is_trusted_admin():
            return "❌ Недостаточно прав для изменения настроек"

        if amount < Decimal("0.1"):
            return "❌ Минимальная сумма не может быть меньше 0.1 USDT"
        if amount > Decimal("1000"):
            return "❌ Минимальная сумма не может быть больше 1000 USDT"

        try:
            repo = GlobalSettingsRepository(self.session, self.redis_client)
            await repo.update_settings(min_withdrawal_amount=amount)
            await self.session.commit()
            logger.info(
                f"[АРЬЯ] Admin {self.admin_telegram_id} set min withdrawal to {amount}"
            )
            return f"✅ Минимальная сумма вывода установлена: `{amount} USDT`"
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error setting min withdrawal: {e}")
            return f"❌ Ошибка: {e}"

    async def toggle_daily_limit(self, enabled: bool) -> str:
        """Toggle daily withdrawal limit."""
        admin, error = await self._verify_admin()
        if error:
            return error
        if not self._is_trusted_admin():
            return "❌ Только доверенные админы могут изменять настройки выводов"

        try:
            repo = GlobalSettingsRepository(self.session, self.redis_client)
            await repo.update_settings(is_daily_limit_enabled=enabled)
            await self.session.commit()
            status = "включено" if enabled else "выключено"
            logger.info(
                f"[АРЬЯ] Admin {self.admin_telegram_id} toggled daily limit: {status}"
            )
            return f"✅ Ограничение дневного лимита {status}"
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error toggling daily limit: {e}")
            return f"❌ Ошибка: {e}"

    async def set_daily_limit(self, amount: Decimal) -> str:
        """Set daily withdrawal limit amount."""
        admin, error = await self._verify_admin()
        if error:
            return error
        if not self._is_trusted_admin():
            return "❌ Только доверенные админы могут изменять настройки выводов"

        if amount < Decimal("10"):
            return "❌ Дневной лимит не может быть меньше 10 USDT"

        try:
            repo = GlobalSettingsRepository(self.session, self.redis_client)
            await repo.update_settings(daily_withdrawal_limit=amount)
            await self.session.commit()
            logger.info(
                f"[АРЬЯ] Admin {self.admin_telegram_id} set daily limit to {amount}"
            )
            return f"✅ Дневной лимит вывода установлен: `{amount} USDT`"
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error setting daily limit: {e}")
            return f"❌ Ошибка: {e}"

    async def toggle_auto_withdrawal(self, enabled: bool) -> str:
        """Toggle auto-withdrawal."""
        admin, error = await self._verify_admin()
        if error:
            return error
        if not self._is_trusted_admin():
            return "❌ Только доверенные админы могут изменять настройки выводов"

        try:
            repo = GlobalSettingsRepository(self.session, self.redis_client)
            await repo.update_settings(auto_withdrawal_enabled=enabled)
            await self.session.commit()
            status = "включен" if enabled else "выключен"
            logger.info(
                f"[АРЬЯ] Admin {self.admin_telegram_id} "
                f"toggled auto withdrawal: {status}"
            )
            return f"✅ Авто-вывод {status}"
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error toggling auto withdrawal: {e}")
            return f"❌ Ошибка: {e}"

    async def set_service_fee(self, fee: Decimal) -> str:
        """Set withdrawal service fee percentage."""
        admin, error = await self._verify_admin()
        if error:
            return error
        if not self._is_trusted_admin():
            return "❌ Только доверенные админы могут изменять настройки выводов"

        if fee < Decimal("0") or fee > Decimal("50"):
            return "❌ Комиссия должна быть от 0% до 50%"

        try:
            repo = GlobalSettingsRepository(self.session, self.redis_client)
            await repo.update_settings(withdrawal_service_fee=fee)
            await self.session.commit()
            logger.info(
                f"[АРЬЯ] Admin {self.admin_telegram_id} set service fee to {fee}%"
            )
            return f"✅ Комиссия сервиса установлена: `{fee}%`"
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error setting service fee: {e}")
            return f"❌ Ошибка: {e}"
