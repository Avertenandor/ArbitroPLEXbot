"""
AI Settings Service.

Provides platform settings management for AI assistant:
- Withdrawal settings (min amount, limits, auto-withdrawal, fees)
- Deposit settings (level corridors, enable/disable levels, PLEX rate)
- Scheduled tasks management

SECURITY:
- Read-only for all admins
- Write operations only for trusted admins
"""

from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.admin_repository import AdminRepository
from app.repositories.global_settings_repository import GlobalSettingsRepository
from app.repositories.deposit_level_config_repository import DepositLevelConfigRepository


# Whitelist of admin telegram IDs who can modify settings
TRUSTED_ADMIN_IDS = [
    1040687384,  # @VladarevInvestBrok (Boss/super_admin)
    1691026253,  # @AI_XAN (Tech Deputy)
    241568583,   # @natder (Наташа)
    6540613027,  # @ded_vtapkax
]


class AISettingsService:
    """
    AI-powered settings management service.
    
    Provides withdrawal and deposit settings management for ARIA.
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
        """Check if current admin is trusted."""
        return self.admin_telegram_id in TRUSTED_ADMIN_IDS

    # ========================================================================
    # WITHDRAWAL SETTINGS
    # ========================================================================

    async def get_withdrawal_settings(self) -> str:
        """Get current withdrawal settings."""
        admin, error = await self._verify_admin()
        if error:
            return error

        try:
            repo = GlobalSettingsRepository(self.session)
            settings = await repo.get_settings()

            limit_status = "✅ Включено" if settings.is_daily_limit_enabled else "❌ Выключено"
            auto_status = "✅ Включен" if settings.auto_withdrawal_enabled else "❌ Выключен"
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
                f"_Авто-вывод работает по правилу x5 (Депозиты * 5 >= Выводы + Запрос)._"
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
            return "❌ Только доверенные админы могут изменять настройки выводов"

        if amount < Decimal("0.1"):
            return "❌ Минимальная сумма не может быть меньше 0.1 USDT"

        if amount > Decimal("1000"):
            return "❌ Минимальная сумма не может быть больше 1000 USDT"

        try:
            repo = GlobalSettingsRepository(self.session)
            await repo.update_settings(min_withdrawal_amount=amount)
            await self.session.commit()

            logger.info(f"[АРЬЯ] Admin {self.admin_telegram_id} set min withdrawal to {amount}")
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
            repo = GlobalSettingsRepository(self.session)
            await repo.update_settings(is_daily_limit_enabled=enabled)
            await self.session.commit()

            status = "включено" if enabled else "выключено"
            logger.info(f"[АРЬЯ] Admin {self.admin_telegram_id} toggled daily limit: {status}")
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
            repo = GlobalSettingsRepository(self.session)
            await repo.update_settings(daily_withdrawal_limit=amount)
            await self.session.commit()

            logger.info(f"[АРЬЯ] Admin {self.admin_telegram_id} set daily limit to {amount}")
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
            repo = GlobalSettingsRepository(self.session)
            await repo.update_settings(auto_withdrawal_enabled=enabled)
            await self.session.commit()

            status = "включен" if enabled else "выключен"
            logger.info(f"[АРЬЯ] Admin {self.admin_telegram_id} toggled auto withdrawal: {status}")
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
            repo = GlobalSettingsRepository(self.session)
            await repo.update_settings(withdrawal_service_fee=fee)
            await self.session.commit()

            logger.info(f"[АРЬЯ] Admin {self.admin_telegram_id} set service fee to {fee}%")
            return f"✅ Комиссия сервиса установлена: `{fee}%`"
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error setting service fee: {e}")
            return f"❌ Ошибка: {e}"

    # ========================================================================
    # DEPOSIT SETTINGS
    # ========================================================================

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

            level_emoji = {
                "test": "🎯",
                "level_1": "💰",
                "level_2": "💎",
                "level_3": "🏆",
                "level_4": "👑",
                "level_5": "🚀",
            }

            lines = ["⚙️ **Настройки уровней депозитов**\n"]
            plex_rate = None

            for level_config in levels:
                emoji = level_emoji.get(level_config.level_type, "📊")
                status = "✅" if level_config.is_active else "❌"
                lines.append(
                    f"{emoji} {level_config.name}: "
                    f"${level_config.min_amount:,.0f} - ${level_config.max_amount:,.0f} {status}"
                )
                if plex_rate is None:
                    plex_rate = level_config.plex_per_dollar

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

        valid_levels = ["test", "level_1", "level_2", "level_3", "level_4", "level_5"]
        if level_type not in valid_levels:
            return f"❌ Неверный уровень. Доступные: {', '.join(valid_levels)}"

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
                f"[АРЬЯ] Admin {self.admin_telegram_id} set {level_type} corridor: "
                f"${min_amount}-${max_amount}"
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

        valid_levels = ["test", "level_1", "level_2", "level_3", "level_4", "level_5"]
        if level_type not in valid_levels:
            return f"❌ Неверный уровень. Доступные: {', '.join(valid_levels)}"

        try:
            config_repo = DepositLevelConfigRepository(self.session)
            level_config = await config_repo.get_by_level_type(level_type)

            if not level_config:
                return f"❌ Уровень {level_type} не найден"

            level_config.is_active = enabled
            self.session.add(level_config)
            await self.session.commit()

            status = "включен" if enabled else "отключен"
            logger.info(f"[АРЬЯ] Admin {self.admin_telegram_id} toggled {level_type}: {status}")
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

            logger.info(f"[АРЬЯ] Admin {self.admin_telegram_id} set PLEX rate to {rate}")
            return f"✅ PLEX за $1 установлен: `{rate}` токенов для всех уровней"

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error setting PLEX rate: {e}")
            return f"❌ Ошибка: {e}"

    # ========================================================================
    # SCHEDULED TASKS
    # ========================================================================

    async def get_scheduled_tasks(self) -> str:
        """Get list of scheduled tasks and their status."""
        admin, error = await self._verify_admin()
        if error:
            return error

        # Task definitions
        tasks = [
            ("💰 Уведомления о балансе", "balance_notifications", "1 час"),
            ("💎 Мониторинг PLEX", "plex_balance_monitor", "1 час"),
            ("📈 Начисление ROI", "daily_rewards", "1 день (00:05 UTC)"),
            ("📦 Мониторинг депозитов", "deposit_monitoring", "1 минута"),
            ("⛓️ Синхронизация блокчейна", "blockchain_cache_sync", "30 секунд"),
            ("🔄 Повтор уведомлений", "notification_retry", "1 минута"),
        ]

        lines = ["📋 **Запланированные задачи**\n"]
        for name, task_id, interval in tasks:
            lines.append(f"• {name}\n  ID: `{task_id}`, Интервал: {interval}")

        lines.append(
            "\n\n💡 Для ручного запуска: `запусти задачу <task_id>`\n"
            "⚠️ Включение/отключение задач требует перезапуска сервисов"
        )

        return "\n".join(lines)

    async def trigger_task(self, task_id: str) -> str:
        """Manually trigger a scheduled task."""
        admin, error = await self._verify_admin()
        if error:
            return error

        if not self._is_trusted_admin():
            return "❌ Только доверенные админы могут запускать задачи вручную"

        valid_tasks = {
            "balance_notifications": "jobs.tasks.balance_notification:send_balance_notifications",
            "plex_balance_monitor": "jobs.tasks.plex_balance_monitor:monitor_plex_balances",
            "daily_rewards": "jobs.tasks.daily_rewards:process_daily_rewards",
            "deposit_monitoring": "jobs.tasks.deposit_monitoring:monitor_deposits",
            "blockchain_cache_sync": "jobs.tasks.blockchain_cache_sync:sync_blockchain_cache",
            "notification_retry": "jobs.tasks.notification_retry:retry_notifications",
        }

        if task_id not in valid_tasks:
            return f"❌ Неизвестная задача. Доступные: {', '.join(valid_tasks.keys())}"

        try:
            # Import and run the task
            module_path, func_name = valid_tasks[task_id].rsplit(":", 1)
            
            # Log the manual trigger
            logger.info(f"[АРЬЯ] Admin {self.admin_telegram_id} triggered task: {task_id}")
            
            return (
                f"⚠️ Ручной запуск задачи `{task_id}` запрошен.\n\n"
                f"Для немедленного выполнения используйте:\n"
                f"`docker compose exec worker python -c \"from {module_path} import {func_name}; "
                f"import asyncio; asyncio.run({func_name}())\"`\n\n"
                f"Или дождитесь следующего цикла по расписанию."
            )

        except Exception as e:
            logger.error(f"Error triggering task {task_id}: {e}")
            return f"❌ Ошибка: {e}"

    # ========================================================================
    # ADMIN MANAGEMENT
    # ========================================================================

    async def create_admin(
        self, telegram_id: int, username: str | None, role: str = "moderator"
    ) -> str:
        """Create a new admin."""
        admin, error = await self._verify_admin()
        if error:
            return error

        # Only super_admin can create admins
        if self.admin_telegram_id != 1040687384:  # Boss
            return "❌ Только владелец платформы может создавать администраторов"

        valid_roles = ["moderator", "admin", "extended_admin"]
        if role not in valid_roles:
            return f"❌ Неверная роль. Доступные: {', '.join(valid_roles)}"

        try:
            admin_repo = AdminRepository(self.session)
            
            # Check if already exists
            existing = await admin_repo.get_by_telegram_id(telegram_id)
            if existing:
                return f"❌ Админ с ID {telegram_id} уже существует (роль: {existing.role})"

            # Create new admin
            from app.models.admin import Admin
            new_admin = Admin(
                telegram_id=telegram_id,
                username=username,
                role=role,
                is_blocked=False,
            )
            self.session.add(new_admin)
            await self.session.commit()

            logger.info(
                f"[АРЬЯ] Super admin created new admin: "
                f"telegram_id={telegram_id}, username={username}, role={role}"
            )
            return (
                f"✅ Администратор создан:\n"
                f"• Telegram ID: `{telegram_id}`\n"
                f"• Username: @{username or 'не указан'}\n"
                f"• Роль: `{role}`"
            )

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating admin: {e}")
            return f"❌ Ошибка: {e}"

    async def delete_admin(self, telegram_id: int) -> str:
        """Delete an admin."""
        admin, error = await self._verify_admin()
        if error:
            return error

        # Only super_admin can delete admins
        if self.admin_telegram_id != 1040687384:  # Boss
            return "❌ Только владелец платформы может удалять администраторов"

        if telegram_id == 1040687384:
            return "❌ Нельзя удалить владельца платформы"

        try:
            admin_repo = AdminRepository(self.session)
            target_admin = await admin_repo.get_by_telegram_id(telegram_id)

            if not target_admin:
                return f"❌ Админ с ID {telegram_id} не найден"

            await self.session.delete(target_admin)
            await self.session.commit()

            logger.info(f"[АРЬЯ] Super admin deleted admin: telegram_id={telegram_id}")
            return f"✅ Администратор с ID `{telegram_id}` удалён"

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error deleting admin: {e}")
            return f"❌ Ошибка: {e}"
