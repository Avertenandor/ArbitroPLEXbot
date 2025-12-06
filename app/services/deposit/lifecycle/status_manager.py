"""
Deposit status manager module.

Handles deposit status transitions and state management.
"""

from datetime import UTC, datetime

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deposit import Deposit
from app.models.enums import TransactionStatus
from app.repositories.deposit_repository import DepositRepository


class DepositStatusManager:
    """Manages deposit status transitions."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize status manager."""
        self.session = session
        self.deposit_repo = DepositRepository(session)

    async def update_status(
        self, deposit_id: int, new_status: str
    ) -> Deposit | None:
        """
        Update deposit status.

        Args:
            deposit_id: Deposit ID
            new_status: New status value

        Returns:
            Updated deposit or None
        """
        try:
            deposit = await self.deposit_repo.update(
                deposit_id,
                status=new_status,
            )

            if deposit:
                await self.session.commit()
                logger.info(
                    f"Deposit {deposit_id} status updated to {new_status}"
                )

            return deposit

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update deposit status: {e}")
            raise

    async def mark_as_completed(self, deposit_id: int) -> Deposit | None:
        """
        Mark deposit as ROI completed.

        Sets is_roi_completed=True and completed_at=now.

        Args:
            deposit_id: Deposit ID

        Returns:
            Updated deposit or None
        """
        try:
            now = datetime.now(UTC)
            deposit = await self.deposit_repo.update(
                deposit_id,
                is_roi_completed=True,
                completed_at=now,
            )

            if deposit:
                await self.session.commit()
                logger.info(f"Deposit {deposit_id} marked as ROI completed")

            return deposit

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to mark deposit as completed: {e}")
            raise

    async def mark_as_blocked(
        self, deposit_id: int, reason: str
    ) -> Deposit | None:
        """
        Mark deposit as blocked.

        Sets status to FAILED with reason logged.

        Args:
            deposit_id: Deposit ID
            reason: Reason for blocking

        Returns:
            Updated deposit or None
        """
        try:
            deposit = await self.deposit_repo.update(
                deposit_id,
                status=TransactionStatus.FAILED.value,
            )

            if deposit:
                await self.session.commit()
                logger.warning(
                    f"Deposit {deposit_id} blocked. Reason: {reason}"
                )

            return deposit

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to mark deposit as blocked: {e}")
            raise

    async def reactivate_deposit(self, deposit_id: int) -> Deposit | None:
        """
        Reactivate blocked deposit.

        Sets status back to CONFIRMED.

        Args:
            deposit_id: Deposit ID

        Returns:
            Updated deposit or None
        """
        try:
            deposit = await self.deposit_repo.update(
                deposit_id,
                status=TransactionStatus.CONFIRMED.value,
            )

            if deposit:
                await self.session.commit()
                logger.info(f"Deposit {deposit_id} reactivated")

            return deposit

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to reactivate deposit: {e}")
            raise
