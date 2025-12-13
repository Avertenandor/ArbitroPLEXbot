"""
Withdrawal balance manager.

Handles balance operations for withdrawal requests including deduction,
restoration, fee calculation, and balance queries.
"""

from decimal import Decimal

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TransactionStatus, TransactionType
from app.models.transaction import Transaction
from app.models.user import User
from app.repositories.global_settings_repository import (
    GlobalSettingsRepository,
)


class WithdrawalBalanceManager:
    """Manages balance operations for withdrawal requests."""

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize withdrawal balance manager.

        Args:
            session: Database session
        """
        self.session = session
        self.settings_repo = GlobalSettingsRepository(session)

    async def deduct_balance(
        self, user_id: int, amount: Decimal, withdrawal_id: int
    ) -> bool:
        """
        Deduct balance from user account for withdrawal.

        Args:
            user_id: User ID
            amount: Amount to deduct (gross amount including fees)
            withdrawal_id: Transaction ID for logging

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get user with lock
            stmt = (
                select(User)
                .where(User.id == user_id)
                .with_for_update()
            )
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.error(
                    "User not found for balance deduction",
                    extra={
                        "user_id": user_id,
                        "withdrawal_id": withdrawal_id,
                    },
                )
                return False

            # Check sufficient balance
            if user.balance < amount:
                logger.warning(
                    "Insufficient balance for deduction",
                    extra={
                        "user_id": user_id,
                        "withdrawal_id": withdrawal_id,
                        "available": str(user.balance),
                        "requested": str(amount),
                    },
                )
                return False

            # Deduct balance
            balance_before = user.balance
            user.balance = user.balance - amount

            logger.info(
                "Balance deducted for withdrawal",
                extra={
                    "user_id": user_id,
                    "withdrawal_id": withdrawal_id,
                    "amount": str(amount),
                    "balance_before": str(balance_before),
                    "balance_after": str(user.balance),
                },
            )

            return True

        except SQLAlchemyError as e:
            logger.error(
                "Failed to deduct balance",
                extra={
                    "user_id": user_id,
                    "withdrawal_id": withdrawal_id,
                    "amount": str(amount),
                    "error": str(e),
                },
                exc_info=True,
            )
            return False

    async def restore_balance(
        self, user_id: int, amount: Decimal, withdrawal_id: int
    ) -> bool:
        """
        Restore balance to user account (for cancelled/rejected withdrawals).

        Args:
            user_id: User ID
            amount: Amount to restore (gross amount that was deducted)
            withdrawal_id: Transaction ID for logging

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get user with lock
            stmt = (
                select(User)
                .where(User.id == user_id)
                .with_for_update()
            )
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.error(
                    "User not found for balance restoration",
                    extra={
                        "user_id": user_id,
                        "withdrawal_id": withdrawal_id,
                    },
                )
                return False

            # Restore balance
            balance_before = user.balance
            user.balance = user.balance + amount

            logger.info(
                "Balance restored for withdrawal",
                extra={
                    "user_id": user_id,
                    "withdrawal_id": withdrawal_id,
                    "amount": str(amount),
                    "balance_before": str(balance_before),
                    "balance_after": str(user.balance),
                },
            )

            return True

        except SQLAlchemyError as e:
            logger.error(
                "Failed to restore balance",
                extra={
                    "user_id": user_id,
                    "withdrawal_id": withdrawal_id,
                    "amount": str(amount),
                    "error": str(e),
                },
                exc_info=True,
            )
            return False

    async def calculate_fee(self, amount: Decimal) -> Decimal:
        """
        Calculate withdrawal service fee.

        Args:
            amount: Gross withdrawal amount

        Returns:
            Fee amount (Decimal)
        """
        try:
            # Load global settings for fee percentage
            global_settings = await self.settings_repo.get_settings()
            service_fee_percent = getattr(
                global_settings, "withdrawal_service_fee", Decimal("0")
            )

            # Calculate fee: amount * (fee_percent / 100)
            fee_amount = amount * (service_fee_percent / Decimal("100"))

            logger.debug(
                "Calculated withdrawal fee",
                extra={
                    "amount": str(amount),
                    "fee_percent": str(service_fee_percent),
                    "fee_amount": str(fee_amount),
                },
            )

            return fee_amount

        except SQLAlchemyError as e:
            logger.error(
                "Failed to calculate fee",
                extra={
                    "amount": str(amount),
                    "error": str(e),
                },
                exc_info=True,
            )
            # CRITICAL: Re-raise exception to prevent withdrawal without fee
            raise ValueError(f"Failed to calculate withdrawal fee: {e}") from e

    async def get_available_balance(self, user_id: int) -> Decimal:
        """
        Get user's available balance (not locked in pending withdrawals).

        Args:
            user_id: User ID

        Returns:
            Available balance (Decimal)
        """
        try:
            stmt = select(User).where(User.id == user_id)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.warning(
                    "User not found when fetching available balance",
                    extra={"user_id": user_id},
                )
                return Decimal("0.00")

            available_balance = getattr(user, "balance", Decimal("0.00"))

            logger.debug(
                "Retrieved available balance",
                extra={
                    "user_id": user_id,
                    "available_balance": str(available_balance),
                },
            )

            return available_balance

        except SQLAlchemyError as e:
            logger.error(
                "Failed to get available balance",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            return Decimal("0.00")

    async def get_pending_withdrawals_total(self, user_id: int) -> Decimal:
        """
        Get total amount of pending withdrawals for user.

        Args:
            user_id: User ID

        Returns:
            Total pending withdrawals amount (Decimal)
        """
        try:
            # Sum all pending and processing withdrawals
            stmt = select(
                func.coalesce(func.sum(Transaction.amount), Decimal("0"))
            ).where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.WITHDRAWAL.value,
                Transaction.status.in_([
                    TransactionStatus.PENDING.value,
                    TransactionStatus.PROCESSING.value,
                ]),
            )

            result = await self.session.execute(stmt)
            pending_total = result.scalar() or Decimal("0.00")

            logger.debug(
                "Retrieved pending withdrawals total",
                extra={
                    "user_id": user_id,
                    "pending_total": str(pending_total),
                },
            )

            return pending_total

        except SQLAlchemyError as e:
            logger.error(
                "Failed to get pending withdrawals total",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            return Decimal("0.00")
