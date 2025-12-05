"""
Admin Event Monitoring Service.

Централизованный сервис для уведомления администраторов о событиях в боте.
Поддерживает категоризацию, приоритеты и форматирование на русском языке.
"""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from loguru import logger

from app.config.constants import TELEGRAM_TIMEOUT

if TYPE_CHECKING:
    from aiogram import Bot
    from sqlalchemy.ext.asyncio import AsyncSession


class EventCategory(StrEnum):
    """Категории событий для мониторинга."""

    # Финансы
    DEPOSIT = "deposit"  # Депозиты
    WITHDRAWAL = "withdrawal"  # Выводы
    PLEX_PAYMENT = "plex_payment"  # Оплата PLEX
    REFERRAL = "referral"  # Реферальные бонусы

    # Безопасность
    SECURITY = "security"  # Безопасность
    SUSPICIOUS = "suspicious"  # Подозрительная активность
    BLACKLIST = "blacklist"  # Чёрный список

    # Пользователи
    USER_REGISTRATION = "user_registration"  # Регистрация
    USER_VERIFICATION = "user_verification"  # Верификация
    USER_RECOVERY = "user_recovery"  # Восстановление аккаунта

    # Поддержка
    SUPPORT = "support"  # Тикеты поддержки
    INQUIRY = "inquiry"  # Вопросы пользователей
    APPEAL = "appeal"  # Апелляции

    # Система
    SYSTEM = "system"  # Системные события
    ERROR = "error"  # Ошибки
    MAINTENANCE = "maintenance"  # Техобслуживание


class EventPriority(StrEnum):
    """Приоритет события."""

    CRITICAL = "critical"  # 🔴 Критический - требует немедленного внимания
    HIGH = "high"  # 🟠 Высокий - важно, но не срочно
    MEDIUM = "medium"  # 🟡 Средний - обычное уведомление
    LOW = "low"  # 🟢 Низкий - информационное


# Эмодзи для категорий
CATEGORY_EMOJI = {
    EventCategory.DEPOSIT: "💰",
    EventCategory.WITHDRAWAL: "💸",
    EventCategory.PLEX_PAYMENT: "💎",
    EventCategory.REFERRAL: "👥",
    EventCategory.SECURITY: "🔒",
    EventCategory.SUSPICIOUS: "🚨",
    EventCategory.BLACKLIST: "⛔",
    EventCategory.USER_REGISTRATION: "👤",
    EventCategory.USER_VERIFICATION: "✅",
    EventCategory.USER_RECOVERY: "🔄",
    EventCategory.SUPPORT: "🎫",
    EventCategory.INQUIRY: "❓",
    EventCategory.APPEAL: "📝",
    EventCategory.SYSTEM: "⚙️",
    EventCategory.ERROR: "❌",
    EventCategory.MAINTENANCE: "🔧",
}

# Эмодзи для приоритетов
PRIORITY_EMOJI = {
    EventPriority.CRITICAL: "🔴",
    EventPriority.HIGH: "🟠",
    EventPriority.MEDIUM: "🟡",
    EventPriority.LOW: "🟢",
}

# Названия категорий на русском
CATEGORY_NAMES_RU = {
    EventCategory.DEPOSIT: "Депозит",
    EventCategory.WITHDRAWAL: "Вывод средств",
    EventCategory.PLEX_PAYMENT: "Оплата PLEX",
    EventCategory.REFERRAL: "Реферальный бонус",
    EventCategory.SECURITY: "Безопасность",
    EventCategory.SUSPICIOUS: "Подозрительная активность",
    EventCategory.BLACKLIST: "Чёрный список",
    EventCategory.USER_REGISTRATION: "Регистрация",
    EventCategory.USER_VERIFICATION: "Верификация",
    EventCategory.USER_RECOVERY: "Восстановление",
    EventCategory.SUPPORT: "Тикет поддержки",
    EventCategory.INQUIRY: "Вопрос пользователя",
    EventCategory.APPEAL: "Апелляция",
    EventCategory.SYSTEM: "Система",
    EventCategory.ERROR: "Ошибка",
    EventCategory.MAINTENANCE: "Техобслуживание",
}

# Названия приоритетов на русском
PRIORITY_NAMES_RU = {
    EventPriority.CRITICAL: "КРИТИЧЕСКИЙ",
    EventPriority.HIGH: "Высокий",
    EventPriority.MEDIUM: "Средний",
    EventPriority.LOW: "Низкий",
}


class AdminEventMonitor:
    """
    Сервис мониторинга событий для администраторов.

    Обеспечивает:
    - Категоризацию событий
    - Приоритизацию уведомлений
    - Форматирование сообщений на русском языке
    - Параллельную отправку всем админам
    """

    def __init__(
        self,
        bot: "Bot",
        session: "AsyncSession",
    ) -> None:
        """
        Инициализация монитора.

        Args:
            bot: Экземпляр бота
            session: Сессия базы данных
        """
        self.bot = bot
        self.session = session

    async def _get_admin_ids(self) -> list[int]:
        """Получить список Telegram ID всех активных админов."""
        from app.repositories.admin_repository import AdminRepository

        admin_repo = AdminRepository(self.session)
        admins = await admin_repo.find_by(is_blocked=False)
        return [admin.telegram_id for admin in admins if admin.telegram_id]

    def _format_message(
        self,
        category: EventCategory,
        priority: EventPriority,
        title: str,
        details: dict[str, Any],
        footer: str | None = None,
    ) -> str:
        """
        Форматировать сообщение для отправки.

        Args:
            category: Категория события
            priority: Приоритет
            title: Заголовок
            details: Детали события (ключ-значение)
            footer: Дополнительный текст в конце

        Returns:
            Отформатированное сообщение
        """
        cat_emoji = CATEGORY_EMOJI.get(category, "📋")
        cat_name = CATEGORY_NAMES_RU.get(category, category.value)
        prio_emoji = PRIORITY_EMOJI.get(priority, "⚪")
        prio_name = PRIORITY_NAMES_RU.get(priority, priority.value)

        # Заголовок
        lines = [
            f"{cat_emoji} *{title}*",
            f"{prio_emoji} Приоритет: {prio_name}",
            f"📂 Категория: {cat_name}",
            "",
        ]

        # Детали
        for key, value in details.items():
            if value is not None:
                # Форматирование значений
                if isinstance(value, Decimal):
                    value = f"{value:,.4f}".rstrip("0").rstrip(".")
                elif isinstance(value, datetime):
                    value = value.strftime("%d.%m.%Y %H:%M:%S")
                elif isinstance(value, bool):
                    value = "Да" if value else "Нет"

                lines.append(f"• {key}: `{value}`")

        # Время события
        lines.append("")
        lines.append(f"🕐 {datetime.now(UTC).strftime('%d.%m.%Y %H:%M:%S')} UTC")

        # Футер
        if footer:
            lines.append("")
            lines.append(f"_{footer}_")

        return "\n".join(lines)

    async def _send_to_admins(
        self,
        message: str,
        priority: EventPriority,
    ) -> int:
        """
        Отправить сообщение всем админам.

        Args:
            message: Текст сообщения
            priority: Приоритет (для логирования)

        Returns:
            Количество успешно уведомлённых админов
        """
        admin_ids = await self._get_admin_ids()

        if not admin_ids:
            logger.warning("Нет активных админов для уведомления")
            return 0

        async def send_to_admin(admin_id: int) -> bool:
            try:
                await asyncio.wait_for(
                    self.bot.send_message(
                        chat_id=admin_id,
                        text=message,
                        parse_mode="Markdown",
                    ),
                    timeout=TELEGRAM_TIMEOUT,
                )
                return True
            except TimeoutError:
                logger.warning(f"Таймаут отправки админу {admin_id}")
                return False
            except Exception as e:
                logger.error(f"Ошибка отправки админу {admin_id}: {e}")
                return False

        # Параллельная отправка
        tasks = [send_to_admin(admin_id) for admin_id in admin_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(
            1 for r in results
            if r is True
        )

        if success_count < len(admin_ids):
            logger.warning(
                f"Уведомлено {success_count}/{len(admin_ids)} админов "
                f"(приоритет: {priority.value})"
            )
        else:
            logger.debug(f"Все {success_count} админов уведомлены")

        return success_count

    async def notify(
        self,
        category: EventCategory,
        priority: EventPriority,
        title: str,
        details: dict[str, Any],
        footer: str | None = None,
    ) -> int:
        """
        Отправить уведомление о событии.

        Args:
            category: Категория события
            priority: Приоритет
            title: Заголовок
            details: Детали события
            footer: Дополнительный текст

        Returns:
            Количество уведомлённых админов
        """
        message = self._format_message(
            category, priority, title, details, footer
        )
        return await self._send_to_admins(message, priority)

    # =========================================================================
    # Готовые методы для типичных событий
    # =========================================================================

    async def notify_new_deposit(
        self,
        user_id: int,
        username: str | None,
        amount: Decimal,
        tx_hash: str,
        deposit_id: int,
        level: int,
    ) -> int:
        """Уведомление о новом депозите."""
        return await self.notify(
            category=EventCategory.DEPOSIT,
            priority=EventPriority.MEDIUM,
            title="Новый депозит создан",
            details={
                "Пользователь": f"{user_id} (@{username or 'нет'})",
                "Сумма": f"{amount} USDT",
                "Депозит": f"#{deposit_id}",
                "Уровень": level,
                "TX Hash": tx_hash[:20] + "...",
            },
        )

    async def notify_deposit_error(
        self,
        user_id: int,
        tx_hash: str,
        error: str,
    ) -> int:
        """Уведомление об ошибке депозита."""
        return await self.notify(
            category=EventCategory.DEPOSIT,
            priority=EventPriority.HIGH,
            title="Ошибка обработки депозита",
            details={
                "Пользователь": user_id,
                "TX Hash": tx_hash,
                "Ошибка": error[:100],
            },
            footer="Требуется ручная проверка",
        )

    async def notify_unidentified_deposit(
        self,
        from_address: str,
        amount: Decimal,
        tx_hash: str,
    ) -> int:
        """Уведомление о неопознанном депозите."""
        return await self.notify(
            category=EventCategory.SUSPICIOUS,
            priority=EventPriority.HIGH,
            title="Неопознанный депозит",
            details={
                "Адрес отправителя": from_address,
                "Сумма": f"{amount} USDT",
                "TX Hash": tx_hash,
            },
            footer="Кошелёк не привязан ни к одному пользователю!",
        )

    async def notify_withdrawal_request(
        self,
        user_id: int,
        username: str | None,
        amount: Decimal,
        to_address: str,
    ) -> int:
        """Уведомление о запросе на вывод."""
        return await self.notify(
            category=EventCategory.WITHDRAWAL,
            priority=EventPriority.MEDIUM,
            title="Новый запрос на вывод",
            details={
                "Пользователь": f"{user_id} (@{username or 'нет'})",
                "Сумма": f"{amount} USDT",
                "Адрес": to_address[:20] + "...",
            },
        )

    async def notify_withdrawal_completed(
        self,
        user_id: int,
        amount: Decimal,
        tx_hash: str,
    ) -> int:
        """Уведомление о выполненном выводе."""
        return await self.notify(
            category=EventCategory.WITHDRAWAL,
            priority=EventPriority.LOW,
            title="Вывод выполнен",
            details={
                "Пользователь": user_id,
                "Сумма": f"{amount} USDT",
                "TX Hash": tx_hash[:20] + "...",
            },
        )

    async def notify_large_transaction(
        self,
        transaction_type: str,
        user_id: int,
        amount: Decimal,
        threshold: Decimal,
    ) -> int:
        """Уведомление о крупной транзакции."""
        return await self.notify(
            category=EventCategory.SECURITY,
            priority=EventPriority.HIGH,
            title="Крупная транзакция",
            details={
                "Тип": transaction_type,
                "Пользователь": user_id,
                "Сумма": f"{amount} USDT",
                "Порог": f"{threshold} USDT",
            },
            footer="Рекомендуется проверить транзакцию",
        )

    async def notify_new_registration(
        self,
        user_id: int,
        username: str | None,
        telegram_id: int,
        referrer_id: int | None = None,
    ) -> int:
        """Уведомление о регистрации пользователя."""
        details = {
            "ID пользователя": user_id,
            "Username": f"@{username}" if username else "нет",
            "Telegram ID": telegram_id,
        }
        if referrer_id:
            details["Пригласил"] = f"ID: {referrer_id}"

        return await self.notify(
            category=EventCategory.USER_REGISTRATION,
            priority=EventPriority.LOW,
            title="Новая регистрация",
            details=details,
        )

    async def notify_new_support_ticket(
        self,
        ticket_id: int,
        user_id: int,
        category: str,
    ) -> int:
        """Уведомление о новом тикете поддержки."""
        return await self.notify(
            category=EventCategory.SUPPORT,
            priority=EventPriority.MEDIUM,
            title="Новое обращение в поддержку",
            details={
                "Тикет": f"#{ticket_id}",
                "Пользователь": user_id,
                "Категория": category,
            },
            footer="Перейдите в админ-панель для обработки",
        )

    async def notify_new_inquiry(
        self,
        inquiry_id: int,
        user_id: int,
        username: str | None,
        question_preview: str,
    ) -> int:
        """Уведомление о новом вопросе пользователя."""
        return await self.notify(
            category=EventCategory.INQUIRY,
            priority=EventPriority.MEDIUM,
            title="Новый вопрос от пользователя",
            details={
                "ID обращения": inquiry_id,
                "Пользователь": f"{user_id} (@{username or 'нет'})",
                "Вопрос": question_preview[:80] + "..." if len(question_preview) > 80 else question_preview,
            },
            footer="Нажмите «❓ Вопросы пользователей» в админ-панели",
        )

    async def notify_security_alert(
        self,
        alert_type: str,
        user_id: int | None,
        details_text: str,
    ) -> int:
        """Уведомление о проблеме безопасности."""
        details = {
            "Тип угрозы": alert_type,
            "Описание": details_text[:150],
        }
        if user_id:
            details["Пользователь"] = user_id

        return await self.notify(
            category=EventCategory.SECURITY,
            priority=EventPriority.CRITICAL,
            title="⚠️ ПРЕДУПРЕЖДЕНИЕ БЕЗОПАСНОСТИ",
            details=details,
            footer="ТРЕБУЕТСЯ НЕМЕДЛЕННОЕ ВНИМАНИЕ!",
        )

    async def notify_user_blacklisted(
        self,
        user_id: int,
        username: str | None,
        reason: str,
        admin_id: int,
    ) -> int:
        """Уведомление о добавлении в чёрный список."""
        return await self.notify(
            category=EventCategory.BLACKLIST,
            priority=EventPriority.HIGH,
            title="Пользователь добавлен в ЧС",
            details={
                "Пользователь": f"{user_id} (@{username or 'нет'})",
                "Причина": reason[:100],
                "Добавил админ": admin_id,
            },
        )

    async def notify_system_error(
        self,
        component: str,
        error: str,
        context: str | None = None,
    ) -> int:
        """Уведомление о системной ошибке."""
        details = {
            "Компонент": component,
            "Ошибка": error[:200],
        }
        if context:
            details["Контекст"] = context[:100]

        return await self.notify(
            category=EventCategory.ERROR,
            priority=EventPriority.CRITICAL,
            title="Системная ошибка",
            details=details,
            footer="Проверьте логи для подробностей",
        )

    async def notify_maintenance_mode(
        self,
        enabled: bool,
        reason: str | None = None,
    ) -> int:
        """Уведомление о режиме техобслуживания."""
        status = "ВКЛЮЧЁН" if enabled else "ОТКЛЮЧЁН"
        details = {"Статус": status}
        if reason:
            details["Причина"] = reason

        return await self.notify(
            category=EventCategory.MAINTENANCE,
            priority=EventPriority.HIGH if enabled else EventPriority.MEDIUM,
            title=f"Режим техобслуживания {status}",
            details=details,
        )

    async def notify_plex_payment(
        self,
        user_id: int,
        amount: int,
        deposit_id: int,
        is_sufficient: bool,
    ) -> int:
        """Уведомление об оплате PLEX."""
        priority = EventPriority.LOW if is_sufficient else EventPriority.MEDIUM
        status = "✅ Достаточно" if is_sufficient else "⚠️ Недостаточно"

        return await self.notify(
            category=EventCategory.PLEX_PAYMENT,
            priority=priority,
            title="Оплата PLEX",
            details={
                "Пользователь": user_id,
                "Сумма PLEX": f"{amount:,}",
                "Депозит": f"#{deposit_id}",
                "Статус": status,
            },
        )

    async def notify_referral_bonus(
        self,
        referrer_id: int,
        referrer_username: str | None,
        amount: Decimal,
        level: int,
        source_user_id: int,
        bonus_type: str,
    ) -> int:
        """Уведомление о реферальном бонусе (только крупные)."""
        # Уведомляем только о крупных бонусах (> 1 USDT)
        if amount < 1:
            return 0

        return await self.notify(
            category=EventCategory.REFERRAL,
            priority=EventPriority.LOW,
            title="Реферальный бонус начислен",
            details={
                "Получатель": f"{referrer_id} (@{referrer_username or 'нет'})",
                "Сумма": f"{amount} USDT",
                "Уровень": level,
                "Источник": f"User #{source_user_id}",
                "Тип": bonus_type,
            },
        )

    async def notify_appeal_created(
        self,
        appeal_id: int,
        user_id: int,
        username: str | None,
        subject: str,
    ) -> int:
        """Уведомление о новой апелляции."""
        return await self.notify(
            category=EventCategory.APPEAL,
            priority=EventPriority.HIGH,
            title="Новая апелляция",
            details={
                "ID апелляции": appeal_id,
                "Пользователь": f"{user_id} (@{username or 'нет'})",
                "Тема": subject[:80],
            },
            footer="Апелляции требуют приоритетного рассмотрения",
        )

    async def notify_finpass_recovery(
        self,
        user_id: int,
        username: str | None,
        method: str,
    ) -> int:
        """Уведомление о запросе восстановления фин. пароля."""
        return await self.notify(
            category=EventCategory.USER_RECOVERY,
            priority=EventPriority.HIGH,
            title="Запрос восстановления фин. пароля",
            details={
                "Пользователь": f"{user_id} (@{username or 'нет'})",
                "Метод": method,
            },
            footer="Проверьте подлинность запроса",
        )


async def get_admin_monitor(
    bot: "Bot",
    session: "AsyncSession",
) -> AdminEventMonitor:
    """
    Получить экземпляр монитора событий.

    Args:
        bot: Экземпляр бота
        session: Сессия БД

    Returns:
        AdminEventMonitor
    """
    return AdminEventMonitor(bot, session)
