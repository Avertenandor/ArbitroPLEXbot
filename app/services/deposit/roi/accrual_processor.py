"""
ROI accrual processor module.

Handles ROI reward accruals and payment processing.
"""

from decimal import Decimal

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.deposit_repository import DepositRepository


class ROIAccrualProcessor:
    """Processes ROI accruals and rewards."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize accrual processor."""
        self.session = session
        self.deposit_repo = DepositRepository(session)

    async def process_accrual(
        self, deposit_id: int, accrual_amount: Decimal
    ) -> bool:
        """
        Process ROI accrual for deposit.

        Updates roi_paid_amount and checks if ROI cap is reached.

        Args:
            deposit_id: Deposit ID
            accrual_amount: Amount to accrue

        Returns:
            True if successful, False otherwise
        """
        try:
            deposit = await self.deposit_repo.find_by_id(deposit_id)

            if not deposit:
                logger.warning(f"Deposit {deposit_id} not found for accrual")
                return False

            # Calculate new paid amount
            current_paid = getattr(deposit, "roi_paid_amount", Decimal("0"))
            new_paid = current_paid + accrual_amount

            # Cap at roi_cap_amount
            if new_paid > deposit.roi_cap_amount:
                new_paid = deposit.roi_cap_amount
                logger.info(
                    f"Deposit {deposit_id} ROI capped at {deposit.roi_cap_amount}"
                )

            # Update deposit
            await self.deposit_repo.update(
                deposit_id,
                roi_paid_amount=new_paid,
            )

            # Check if completed
            if new_paid >= deposit.roi_cap_amount:
                from app.services.deposit.lifecycle.status_manager import (
                    DepositStatusManager,
                )

                status_manager = DepositStatusManager(self.session)
                await status_manager.mark_as_completed(deposit_id)

            await self.session.commit()
            logger.info(
                f"Accrual processed for deposit {deposit_id}: "
                f"+{accrual_amount} (total: {new_paid}/{deposit.roi_cap_amount})"
            )

            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to process accrual for deposit {deposit_id}: {e}")
            return False

    async def get_pending_accruals(self) -> list:
        """
        Get deposits pending accrual.

        Returns deposits where next_accrual_at <= now and ROI not completed.

        Returns:
            List of deposits pending accrual
        """
        from datetime import UTC, datetime

        from sqlalchemy import select

        from app.models.deposit import Deposit
        from app.models.enums import TransactionStatus

        now = datetime.now(UTC)

        stmt = (
            select(Deposit)
            .where(
                Deposit.status == TransactionStatus.CONFIRMED.value,
                Deposit.is_roi_completed.is_(False),
                Deposit.next_accrual_at <= now,
            )
            .order_by(Deposit.next_accrual_at)
        )

        result = await self.session.execute(stmt)
        deposits = result.scalars().all()

        return list(deposits)

    async def schedule_next_accrual(
        self, deposit_id: int, hours_from_now: int
    ) -> bool:
        """
        Schedule next accrual for deposit.

        Args:
            deposit_id: Deposit ID
            hours_from_now: Hours until next accrual

        Returns:
            True if successful
        """
        from datetime import UTC, datetime, timedelta

        try:
            next_accrual = datetime.now(UTC) + timedelta(hours=hours_from_now)

            await self.deposit_repo.update(
                deposit_id,
                next_accrual_at=next_accrual,
            )

            await self.session.commit()
            logger.info(
                f"Next accrual scheduled for deposit {deposit_id} at {next_accrual}"
            )

            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Failed to schedule next accrual for deposit {deposit_id}: {e}"
            )
            return False
