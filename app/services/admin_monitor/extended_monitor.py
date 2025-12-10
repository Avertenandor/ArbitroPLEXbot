"""
Admin Event Monitor - Extended Monitor with Specialized Notifications.

This module provides the AdminEventMonitor class extended with all
specialized notification methods for backward compatibility.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from .monitor import AdminEventMonitor as BaseAdminEventMonitor
from .notifications import (
    notify_appeal_created,
    notify_deposit_error,
    notify_finpass_recovery,
    notify_large_transaction,
    notify_maintenance_mode,
    notify_new_deposit,
    notify_new_inquiry,
    notify_new_registration,
    notify_new_support_ticket,
    notify_plex_payment,
    notify_referral_bonus,
    notify_security_alert,
    notify_system_error,
    notify_unidentified_deposit,
    notify_user_blacklisted,
    notify_withdrawal_completed,
    notify_withdrawal_request,
)


if TYPE_CHECKING:
    from aiogram import Bot
    from sqlalchemy.ext.asyncio import AsyncSession


class AdminEventMonitor(BaseAdminEventMonitor):
    """
    Extended AdminEventMonitor with specialized notification methods.

    This class extends the base monitor with convenience methods for
    common notification scenarios.
    """

    # =========================================================================
    # Financial notifications
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
        return await notify_new_deposit(
            self, user_id, username, amount, tx_hash, deposit_id, level
        )

    async def notify_deposit_error(
        self,
        user_id: int,
        tx_hash: str,
        error: str,
    ) -> int:
        """Уведомление об ошибке депозита."""
        return await notify_deposit_error(self, user_id, tx_hash, error)

    async def notify_unidentified_deposit(
        self,
        from_address: str,
        amount: Decimal,
        tx_hash: str,
    ) -> int:
        """Уведомление о неопознанном депозите."""
        return await notify_unidentified_deposit(
            self, from_address, amount, tx_hash
        )

    async def notify_withdrawal_request(
        self,
        user_id: int,
        username: str | None,
        amount: Decimal,
        to_address: str,
    ) -> int:
        """Уведомление о запросе на вывод."""
        return await notify_withdrawal_request(
            self, user_id, username, amount, to_address
        )

    async def notify_withdrawal_completed(
        self,
        user_id: int,
        amount: Decimal,
        tx_hash: str,
    ) -> int:
        """Уведомление о выполненном выводе."""
        return await notify_withdrawal_completed(
            self, user_id, amount, tx_hash
        )

    async def notify_large_transaction(
        self,
        transaction_type: str,
        user_id: int,
        amount: Decimal,
        threshold: Decimal,
    ) -> int:
        """Уведомление о крупной транзакции."""
        return await notify_large_transaction(
            self, transaction_type, user_id, amount, threshold
        )

    async def notify_plex_payment(
        self,
        user_id: int,
        amount: int,
        deposit_id: int,
        is_sufficient: bool,
    ) -> int:
        """Уведомление об оплате PLEX."""
        return await notify_plex_payment(
            self, user_id, amount, deposit_id, is_sufficient
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
        """Уведомление о реферальном бонусе."""
        return await notify_referral_bonus(
            self, referrer_id, referrer_username, amount, level,
            source_user_id, bonus_type
        )

    # =========================================================================
    # Security notifications
    # =========================================================================

    async def notify_security_alert(
        self,
        alert_type: str,
        user_id: int | None,
        details_text: str,
    ) -> int:
        """Уведомление о проблеме безопасности."""
        return await notify_security_alert(
            self, alert_type, user_id, details_text
        )

    async def notify_user_blacklisted(
        self,
        user_id: int,
        username: str | None,
        reason: str,
        admin_id: int,
    ) -> int:
        """Уведомление о добавлении в чёрный список."""
        return await notify_user_blacklisted(
            self, user_id, username, reason, admin_id
        )

    # =========================================================================
    # User notifications
    # =========================================================================

    async def notify_new_registration(
        self,
        user_id: int,
        username: str | None,
        telegram_id: int,
        referrer_id: int | None = None,
    ) -> int:
        """Уведомление о регистрации пользователя."""
        return await notify_new_registration(
            self, user_id, username, telegram_id, referrer_id
        )

    async def notify_finpass_recovery(
        self,
        user_id: int,
        username: str | None,
        method: str,
    ) -> int:
        """Уведомление о запросе восстановления фин. пароля."""
        return await notify_finpass_recovery(
            self, user_id, username, method
        )

    # =========================================================================
    # Support notifications
    # =========================================================================

    async def notify_new_support_ticket(
        self,
        ticket_id: int,
        user_id: int,
        category: str,
    ) -> int:
        """Уведомление о новом тикете поддержки."""
        return await notify_new_support_ticket(
            self, ticket_id, user_id, category
        )

    async def notify_new_inquiry(
        self,
        inquiry_id: int,
        user_id: int,
        username: str | None,
        question_preview: str,
    ) -> int:
        """Уведомление о новом вопросе пользователя."""
        return await notify_new_inquiry(
            self, inquiry_id, user_id, username, question_preview
        )

    async def notify_appeal_created(
        self,
        appeal_id: int,
        user_id: int,
        username: str | None,
        subject: str,
    ) -> int:
        """Уведомление о новой апелляции."""
        return await notify_appeal_created(
            self, appeal_id, user_id, username, subject
        )

    # =========================================================================
    # System notifications
    # =========================================================================

    async def notify_system_error(
        self,
        component: str,
        error: str,
        context: str | None = None,
    ) -> int:
        """Уведомление о системной ошибке."""
        return await notify_system_error(
            self, component, error, context
        )

    async def notify_maintenance_mode(
        self,
        enabled: bool,
        reason: str | None = None,
    ) -> int:
        """Уведомление о режиме техобслуживания."""
        return await notify_maintenance_mode(self, enabled, reason)


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
