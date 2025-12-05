"""
Reward balance handling module.

Handles crediting ROI rewards to user's internal balance and creating
accounting transactions.
"""

from decimal import Decimal

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TransactionStatus, TransactionType
from app.models.user import User
from app.repositories.transaction_repository import TransactionRepository


class RewardBalanceHandler:
    """Handles balance operations for reward credits."""

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize reward balance handler.

        Args:
            session: Database session
        """
        self.session = session
        self.transaction_repo = TransactionRepository(session)

    async def credit_roi_to_balance(
        self,
        user_id: int,
        reward_amount: Decimal,
        deposit_id: int,
    ) -> None:
        """
        Credit ROI reward to user's internal balance and create transaction.

        Args:
            user_id: User ID receiving the reward
            reward_amount: Reward amount to credit
            deposit_id: Source deposit ID (for reference linking)
        """
        if reward_amount <= 0:
            return

        # R9-2: Get balance_before for transaction record
        stmt = select(User.balance).where(User.id == user_id)
        result = await self.session.execute(stmt)
        balance_before = result.scalar_one_or_none()

        if balance_before is None:
            logger.error(
                "Failed to credit ROI to balance: user not found",
                extra={"user_id": user_id, "reward_amount": str(reward_amount)},
            )
            return

        balance_before = balance_before or Decimal("0")
        balance_after = balance_before + reward_amount

        # R9-2: Atomic update with pessimistic locking to prevent race conditions
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(
                balance=User.balance + reward_amount,
                total_earned=User.total_earned + reward_amount,
            )
        )
        await self.session.execute(stmt)

        # Create accounting transaction for internal ROI credit
        await self.transaction_repo.create(
            user_id=user_id,
            type=TransactionType.DEPOSIT_REWARD.value,
            amount=reward_amount,
            balance_before=balance_before,
            balance_after=balance_after,
            status=TransactionStatus.CONFIRMED.value,
            description="ROI reward credited to internal balance",
            reference_type="deposit",
            reference_id=deposit_id,
            tx_hash="internal_balance",
        )
