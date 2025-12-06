"""
Процессор PLEX платежей.
Обработка ожидающих платежей, отправка предупреждений и блокировка.
"""

from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deposit import Deposit
from app.models.plex_payment import PlexPaymentRequirement, PlexPaymentStatus


class PlexPaymentProcessor:
    """Процессор PLEX платежей."""

    WARNING_HOURS = 25
    BLOCK_HOURS = 49

    def __init__(self, session: AsyncSession):
        """
        Инициализация процессора.

        Args:
            session: Сессия базы данных
        """
        self.session = session

    async def mark_payment_received(
        self,
        requirement_id: int,
        tx_hash: str,
        amount: Decimal,
    ) -> bool:
        """
        Отметить получение PLEX платежа.

        Args:
            requirement_id: ID PlexPaymentRequirement
            tx_hash: Хэш транзакции
            amount: Сумма платежа

        Returns:
            True если успешно
        """
        try:
            stmt = select(PlexPaymentRequirement).where(
                PlexPaymentRequirement.id == requirement_id
            )
            result = await self.session.execute(stmt)
            requirement = result.scalar_one_or_none()

            if not requirement:
                logger.error(
                    f"PlexPaymentRequirement {requirement_id} not found"
                )
                return False

            # Используем метод модели для обновления
            requirement.mark_paid(tx_hash=tx_hash, amount=amount)

            await self.session.commit()

            logger.success(
                f"PLEX payment marked as received for deposit "
                f"{requirement.deposit_id} (tx: {tx_hash})"
            )

            return True

        except Exception as e:
            logger.error(f"Error marking PLEX payment as received: {e}")
            await self.session.rollback()
            return False

    async def mark_warning_sent(
        self,
        user_id: int,
        deposit_id: int,
    ) -> bool:
        """
        Отметить отправку предупреждения.

        Args:
            user_id: ID пользователя
            deposit_id: ID депозита

        Returns:
            True если успешно
        """
        try:
            stmt = select(PlexPaymentRequirement).where(
                PlexPaymentRequirement.user_id == user_id,
                PlexPaymentRequirement.deposit_id == deposit_id,
            )
            result = await self.session.execute(stmt)
            requirement = result.scalar_one_or_none()

            if not requirement:
                logger.error(
                    f"PlexPaymentRequirement not found for deposit {deposit_id}"
                )
                return False

            requirement.mark_warning_sent()
            await self.session.commit()

            logger.info(f"Warning marked as sent for deposit {deposit_id}")
            return True

        except Exception as e:
            logger.error(f"Error marking warning as sent: {e}")
            await self.session.rollback()
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
            # Обновляем PlexPaymentRequirement
            stmt = select(PlexPaymentRequirement).where(
                PlexPaymentRequirement.deposit_id == deposit_id
            )
            result = await self.session.execute(stmt)
            requirement = result.scalar_one_or_none()

            if not requirement:
                logger.error(
                    f"PlexPaymentRequirement not found for deposit {deposit_id}"
                )
                return False

            requirement.mark_blocked()

            # Обновляем депозит
            stmt = select(Deposit).where(Deposit.id == deposit_id)
            result = await self.session.execute(stmt)
            deposit = result.scalar_one_or_none()

            if not deposit:
                logger.error(f"Deposit {deposit_id} not found")
                return False

            # Блокируем депозит (ставим специальный статус)
            deposit.status = "blocked_plex_payment"

            await self.session.commit()

            logger.warning(
                f"Deposit {deposit_id} blocked due to PLEX non-payment: {reason}"
            )

            return True

        except Exception as e:
            logger.error(f"Error blocking deposit for PLEX non-payment: {e}")
            await self.session.rollback()
            return False

    async def get_pending_payments(self) -> list[PlexPaymentRequirement]:
        """
        Получить все ожидающие PLEX платежи.

        Returns:
            Список PlexPaymentRequirement со статусом active или warning
        """
        stmt = select(PlexPaymentRequirement).where(
            PlexPaymentRequirement.status.in_([
                PlexPaymentStatus.ACTIVE,
                PlexPaymentStatus.WARNING_SENT,
            ])
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def process_all_pending(
        self,
        check_callback,
        on_paid_callback=None,
        on_warning_callback=None,
        on_blocked_callback=None,
    ) -> dict[str, Any]:
        """
        Обработать все ожидающие PLEX платежи.

        Args:
            check_callback: Функция для проверки платежа
            on_paid_callback: Callback при оплате (опционально)
            on_warning_callback: Callback при предупреждении (опционально)
            on_blocked_callback: Callback при блокировке (опционально)

        Returns:
            {
                "checked": int,
                "paid": int,
                "warnings_sent": int,
                "blocked": int
            }
        """
        logger.info("Processing pending PLEX payments...")

        stats = {
            "checked": 0,
            "paid": 0,
            "warnings_sent": 0,
            "blocked": 0,
        }

        requirements = await self.get_pending_payments()
        logger.info(f"Found {len(requirements)} pending PLEX payments to check")

        for requirement in requirements:
            stats["checked"] += 1

            try:
                # Проверяем платёж через callback
                payment_status = await check_callback(
                    user_id=requirement.user_id,
                    deposit_id=requirement.deposit_id,
                )

                # Обрабатываем результат
                if payment_status["status"] == "paid":
                    stats["paid"] += 1
                    logger.info(
                        f"PLEX payment confirmed for deposit {requirement.deposit_id}"
                    )

                    if on_paid_callback:
                        await on_paid_callback(requirement, payment_status)

                elif payment_status["status"] == "warning":
                    # Отправляем предупреждение только если еще не отправляли
                    if requirement.status != PlexPaymentStatus.WARNING_SENT:
                        stats["warnings_sent"] += 1

                        if on_warning_callback:
                            await on_warning_callback(requirement, payment_status)

                elif payment_status["status"] == "overdue":
                    stats["blocked"] += 1

                    if on_blocked_callback:
                        await on_blocked_callback(requirement, payment_status)

            except Exception as e:
                logger.error(
                    f"Error processing PLEX payment for deposit "
                    f"{requirement.deposit_id}: {e}"
                )
                continue

        logger.info(
            f"PLEX payment processing complete: {stats['checked']} checked, "
            f"{stats['paid']} paid, {stats['warnings_sent']} warnings sent, "
            f"{stats['blocked']} blocked"
        )

        return stats
