"""
Сервис мониторинга ежедневных PLEX платежей.
Проверяет поступление PLEX токенов для активных депозитов.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deposit import Deposit
from app.models.plex_payment import PlexPaymentRequirement, PlexPaymentStatus
from app.repositories.global_settings_repository import GlobalSettingsRepository
from app.services.blockchain.blockchain_service import BlockchainService

from .processor import PlexPaymentProcessor
from .scanner import PlexTransferScanner


class PlexPaymentMonitor:
    """Мониторинг ежедневных PLEX платежей."""

    PLEX_PER_DOLLAR = 10
    WARNING_HOURS = 25
    BLOCK_HOURS = 49

    def __init__(
        self,
        session: AsyncSession,
        blockchain: BlockchainService,
    ):
        """
        Инициализация монитора PLEX платежей.

        Args:
            session: Сессия базы данных
            blockchain: Сервис блокчейна
        """
        self.session = session
        self.blockchain = blockchain

        # Компоненты
        self.scanner = PlexTransferScanner(blockchain)
        self.processor = PlexPaymentProcessor(session)

    async def check_user_plex_payment(
        self,
        user_id: int,
        deposit_id: int,
    ) -> dict[str, Any]:
        """
        Проверить PLEX платёж пользователя за сегодня.

        Args:
            user_id: ID пользователя
            deposit_id: ID депозита

        Returns:
            {
                "status": "paid" | "pending" | "warning" | "overdue",
                "required": Decimal,
                "received": Decimal,
                "tx_hash": str | None,
                "hours_overdue": int
            }
        """
        # Получаем PlexPaymentRequirement
        stmt = select(PlexPaymentRequirement).where(
            PlexPaymentRequirement.user_id == user_id,
            PlexPaymentRequirement.deposit_id == deposit_id,
        )
        result = await self.session.execute(stmt)
        requirement = result.scalar_one_or_none()

        if not requirement:
            logger.warning(f"PLEX payment requirement not found for deposit {deposit_id}")
            return {
                "status": "error",
                "required": Decimal("0"),
                "received": Decimal("0"),
                "tx_hash": None,
                "hours_overdue": 0,
            }

        # Нормализуем дедлайны под глобальный старт проекта,
        # чтобы старые депозиты не улетали сразу в warning/blocked.
        settings_repo = GlobalSettingsRepository(self.session)
        project_start_at = await settings_repo.get_project_start_at()

        now = datetime.now(UTC)
        if requirement.next_payment_due < project_start_at:
            requirement.next_payment_due = project_start_at + timedelta(hours=24)
            requirement.warning_due = project_start_at + timedelta(hours=25)
            requirement.block_due = project_start_at + timedelta(hours=49)
            # Сбрасываем «исторические» предупреждения, чтобы запуск был чистым
            requirement.warning_sent_at = None
            requirement.warning_count = 0
            requirement.last_check_at = now
            # Не разлочиваем вручную заблокированные статусы, только выравниваем таймеры
            if requirement.status in (PlexPaymentStatus.WARNING_SENT, PlexPaymentStatus.OVERDUE):
                requirement.status = PlexPaymentStatus.ACTIVE
            await self.session.commit()

        # Проверяем статус
        hours_overdue = max(0, int((now - requirement.next_payment_due).total_seconds() / 3600))

        # Если уже оплачено
        if requirement.status == PlexPaymentStatus.PAID:
            # Проверяем, не наступил ли новый цикл
            if now >= requirement.next_payment_due:
                # Новый цикл - нужен новый платеж
                requirement.status = PlexPaymentStatus.ACTIVE
                await self.session.commit()

                return {
                    "status": "pending",
                    "required": requirement.daily_plex_required,
                    "received": Decimal("0"),
                    "tx_hash": None,
                    "hours_overdue": hours_overdue,
                }
            else:
                return {
                    "status": "paid",
                    "required": requirement.daily_plex_required,
                    "received": requirement.daily_plex_required,
                    "tx_hash": requirement.last_payment_tx_hash,
                    "hours_overdue": 0,
                }

        # Если заблокирован
        if requirement.status == PlexPaymentStatus.BLOCKED:
            return {
                "status": "blocked",
                "required": requirement.daily_plex_required,
                "received": Decimal("0"),
                "tx_hash": None,
                "hours_overdue": hours_overdue,
            }

        # Получаем кошелек пользователя из депозита
        stmt = select(Deposit).where(Deposit.id == deposit_id)
        result = await self.session.execute(stmt)
        deposit = result.scalar_one_or_none()

        if not deposit or not deposit.wallet_address:
            logger.error(f"Deposit {deposit_id} not found or no wallet address")
            return {
                "status": "error",
                "required": requirement.daily_plex_required,
                "received": Decimal("0"),
                "tx_hash": None,
                "hours_overdue": hours_overdue,
            }

        # Сканируем блокчейн на наличие PLEX платежа
        scan_result = await self.scanner.scan_transfers(
            from_address=deposit.wallet_address,
            required_amount=requirement.daily_plex_required,
            since_hours=24,
        )

        if scan_result["found"]:
            # Платёж найден - обновляем статус
            await self.processor.mark_payment_received(
                requirement_id=requirement.id,
                tx_hash=scan_result["tx_hash"],
                amount=scan_result["amount"],
            )

            return {
                "status": "paid",
                "required": requirement.daily_plex_required,
                "received": scan_result["amount"],
                "tx_hash": scan_result["tx_hash"],
                "hours_overdue": 0,
            }

        # Платёж не найден - проверяем дедлайны
        if requirement.is_block_due():
            return {
                "status": "overdue",
                "required": requirement.daily_plex_required,
                "received": Decimal("0"),
                "tx_hash": None,
                "hours_overdue": hours_overdue,
            }
        elif requirement.is_warning_due():
            return {
                "status": "warning",
                "required": requirement.daily_plex_required,
                "received": Decimal("0"),
                "tx_hash": None,
                "hours_overdue": hours_overdue,
            }
        else:
            return {
                "status": "pending",
                "required": requirement.daily_plex_required,
                "received": Decimal("0"),
                "tx_hash": None,
                "hours_overdue": hours_overdue,
            }

    async def scan_plex_transfers(
        self,
        from_address: str,
        required_amount: Decimal,
        since_hours: int = 24,
    ) -> dict[str, Any]:
        """
        Сканировать блокчейн на наличие PLEX переводов.

        Делегирует работу PlexTransferScanner.

        Args:
            from_address: Адрес отправителя
            required_amount: Требуемая сумма PLEX
            since_hours: Количество часов назад для сканирования

        Returns:
            {
                "found": bool,
                "amount": Decimal,
                "tx_hash": str | None,
                "block_number": int | None
            }
        """
        return await self.scanner.scan_transfers(
            from_address=from_address,
            required_amount=required_amount,
            since_hours=since_hours,
        )

    async def process_pending_payments(self) -> dict[str, Any]:
        """
        Обработать все ожидающие PLEX платежи.
        Вызывается периодически из job.

        Returns:
            {
                "checked": int,
                "paid": int,
                "warnings_sent": int,
                "blocked": int
            }
        """

        # Callback для проверки платежа
        async def check_callback(user_id: int, deposit_id: int):
            return await self.check_user_plex_payment(user_id, deposit_id)

        # Callback при оплате
        async def on_paid(requirement, payment_status):
            from app.models.user import User
            from bot.main import bot_instance

            if bot_instance:
                from .notifier import PlexPaymentNotifier

                stmt = select(User.telegram_id).where(User.id == requirement.user_id)
                result = await self.session.execute(stmt)
                telegram_id = result.scalar_one_or_none()

                if telegram_id:
                    notifier = PlexPaymentNotifier(bot_instance, self.session)
                    await notifier.notify_payment_received(
                        user_telegram_id=telegram_id,
                        deposit_id=requirement.deposit_id,
                        amount=payment_status["received"],
                        tx_hash=payment_status["tx_hash"],
                    )

        # Callback при предупреждении
        async def on_warning(requirement, payment_status):
            hours_left = self.BLOCK_HOURS - payment_status["hours_overdue"]
            await self.send_warning(
                user_id=requirement.user_id,
                deposit_id=requirement.deposit_id,
                hours_left=hours_left,
            )

        # Callback при блокировке
        async def on_blocked(requirement, payment_status):
            await self.block_deposit(
                deposit_id=requirement.deposit_id,
                reason="PLEX payment overdue (49h without payment)",
            )

        # Обрабатываем через processor
        return await self.processor.process_all_pending(
            check_callback=check_callback,
            on_paid_callback=on_paid,
            on_warning_callback=on_warning,
            on_blocked_callback=on_blocked,
        )

    async def mark_payment_received(
        self,
        requirement_id: int,
        tx_hash: str,
        amount: Decimal,
    ) -> bool:
        """
        Отметить получение PLEX платежа.

        Делегирует работу PlexPaymentProcessor.

        Args:
            requirement_id: ID PlexPaymentRequirement
            tx_hash: Хэш транзакции
            amount: Сумма платежа

        Returns:
            True если успешно
        """
        return await self.processor.mark_payment_received(
            requirement_id=requirement_id,
            tx_hash=tx_hash,
            amount=amount,
        )

    async def send_warning(
        self,
        user_id: int,
        deposit_id: int,
        hours_left: int,
    ) -> bool:
        """
        Отправить предупреждение о необходимости PLEX платежа.

        Args:
            user_id: ID пользователя
            deposit_id: ID депозита
            hours_left: Часов осталось до блокировки

        Returns:
            True если успешно
        """
        try:
            # Обновляем статус через processor
            await self.processor.mark_warning_sent(user_id, deposit_id)

            # Отправляем уведомление
            from app.models.user import User
            from bot.main import bot_instance

            if bot_instance:
                from .notifier import PlexPaymentNotifier

                # Получаем telegram_id и requirement
                stmt = select(User.telegram_id).where(User.id == user_id)
                result = await self.session.execute(stmt)
                telegram_id = result.scalar_one_or_none()

                stmt = select(PlexPaymentRequirement).where(
                    PlexPaymentRequirement.user_id == user_id,
                    PlexPaymentRequirement.deposit_id == deposit_id,
                )
                result = await self.session.execute(stmt)
                requirement = result.scalar_one_or_none()

                if telegram_id and requirement:
                    notifier = PlexPaymentNotifier(bot_instance, self.session)
                    await notifier.notify_warning(
                        user_telegram_id=telegram_id,
                        deposit_id=deposit_id,
                        hours_left=hours_left,
                        required_amount=requirement.daily_plex_required,
                    )

            logger.info(f"Warning sent for deposit {deposit_id} ({hours_left}h until block)")
            return True

        except Exception as e:
            logger.error(f"Error sending PLEX payment warning: {e}")
            return False

    async def block_deposit(
        self,
        deposit_id: int,
        reason: str,
    ) -> bool:
        """
        Заблокировать депозит за неоплату PLEX.

        Args:
            deposit_id: ID депозита
            reason: Причина блокировки

        Returns:
            True если успешно
        """
        try:
            # Блокируем через processor
            success = await self.processor.block_deposit(deposit_id, reason)
            if not success:
                return False

            # Отправляем уведомление
            from app.models.user import User
            from bot.main import bot_instance

            if bot_instance:
                from .notifier import PlexPaymentNotifier

                # Получаем telegram_id
                stmt = select(PlexPaymentRequirement).where(PlexPaymentRequirement.deposit_id == deposit_id)
                result = await self.session.execute(stmt)
                requirement = result.scalar_one_or_none()

                if requirement:
                    stmt = select(User.telegram_id).where(User.id == requirement.user_id)
                    result = await self.session.execute(stmt)
                    telegram_id = result.scalar_one_or_none()

                    if telegram_id:
                        notifier = PlexPaymentNotifier(bot_instance, self.session)
                        await notifier.notify_deposit_blocked(
                            user_telegram_id=telegram_id,
                            deposit_id=deposit_id,
                            reason=reason,
                        )

            return True

        except Exception as e:
            logger.error(f"Error blocking deposit for PLEX non-payment: {e}")
            return False
