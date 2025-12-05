"""
Withdrawal helper functions module.

Provides utility functions for withdrawal operations including
daily limit checks and finpass recovery handling.
"""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deposit_reward import DepositReward
from app.models.enums import TransactionStatus, TransactionType
from app.models.transaction import Transaction
from app.repositories.deposit_repository import DepositRepository


class WithdrawalHelpers:
    """Helper utilities for withdrawal operations."""

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize withdrawal helpers.

        Args:
            session: Database session
        """
        self.session = session

    async def check_daily_withdrawal_limit(
        self, user_id: int, requested_amount: Decimal
    ) -> dict:
        """
        Check if withdrawal exceeds daily limit (= daily ROI).

        Args:
            user_id: User ID
            requested_amount: Requested withdrawal amount

        Returns:
            Dict with exceeded, daily_roi, withdrawn_today, remaining
        """
        # Create timezone-aware datetime for DepositReward.calculated_at (has timezone=True)
        today = datetime.now(UTC).date()
        today_start_aware = datetime(today.year, today.month, today.day, tzinfo=UTC)
        # Create naive datetime for Transaction.created_at (TIMESTAMP WITHOUT TIME ZONE)
        today_start_naive = datetime(today.year, today.month, today.day)

        # Calculate today's ROI (sum of rewards accrued today)
        # DepositReward.calculated_at is timezone-aware, use aware datetime
        stmt = select(func.coalesce(func.sum(DepositReward.reward_amount), Decimal("0"))).where(
            DepositReward.user_id == user_id,
            DepositReward.calculated_at >= today_start_aware,
        )
        result = await self.session.execute(stmt)
        daily_roi = result.scalar() or Decimal("0")

        # If no ROI today, calculate expected daily ROI from active deposits
        if daily_roi == Decimal("0"):
            deposit_repo = DepositRepository(self.session)
            active_deposits = await deposit_repo.get_active_deposits(user_id)
            for deposit in active_deposits:
                if deposit.deposit_version and deposit.deposit_version.roi_percent:
                    daily_roi += (deposit.amount * deposit.deposit_version.roi_percent) / 100

        # Get today's withdrawals (pending, processing, completed)
        # Transaction.created_at is naive, use naive datetime
        stmt = select(func.coalesce(func.sum(Transaction.amount), Decimal("0"))).where(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.WITHDRAWAL.value,
            Transaction.status.in_([
                TransactionStatus.CONFIRMED.value,
                TransactionStatus.PROCESSING.value,
                TransactionStatus.PENDING.value,
            ]),
            Transaction.created_at >= today_start_naive,
        )
        result = await self.session.execute(stmt)
        withdrawn_today = result.scalar() or Decimal("0")

        # Calculate remaining
        remaining = max(daily_roi - withdrawn_today, Decimal("0"))

        # Check if exceeded (only if there's a daily ROI limit)
        exceeded = False
        if daily_roi > Decimal("0"):
            exceeded = (withdrawn_today + requested_amount) > daily_roi

        return {
            "exceeded": exceeded,
            "daily_roi": float(daily_roi),
            "withdrawn_today": float(withdrawn_today),
            "remaining": float(remaining),
        }

    async def handle_successful_withdrawal_with_old_password(
        self, user_id: int
    ) -> None:
        """
        Handle successful withdrawal with old password.

        If a user successfully withdraws with their old password while
        a finpass recovery is pending, the recovery should be rejected
        as it proves they have access to their account.

        Args:
            user_id: User ID
        """
        from app.services.finpass_recovery_service import (
            FinpassRecoveryService,
        )

        finpass_service = FinpassRecoveryService(self.session)
        active_recovery = await finpass_service.get_pending_by_user(user_id)

        if active_recovery:
            await finpass_service.reject_recovery(
                recovery_id=active_recovery.id,
                admin_id=None,
                reason="User successfully withdrew with old password",
            )
