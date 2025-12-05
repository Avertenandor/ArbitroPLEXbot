"""
Payment Retry Service - Core Module.

Module: core.py
Contains the main PaymentRetryService class initialization and retry record creation.
Handles creating and updating retry records for failed payments.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment_retry import PaymentRetry, PaymentType
from app.repositories.deposit_reward_repository import DepositRewardRepository
from app.repositories.payment_retry_repository import PaymentRetryRepository
from app.repositories.referral_earning_repository import ReferralEarningRepository
from app.repositories.transaction_repository import TransactionRepository

from .constants import BASE_RETRY_DELAY_MINUTES, DEFAULT_MAX_RETRIES


class PaymentRetryCore:
    """Core retry record management."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize core components."""
        self.session = session
        self.retry_repo = PaymentRetryRepository(session)
        self.earning_repo = ReferralEarningRepository(session)
        self.reward_repo = DepositRewardRepository(session)
        self.transaction_repo = TransactionRepository(session)

    async def create_retry_record(
        self,
        user_id: int,
        amount: Decimal,
        payment_type: PaymentType,
        earning_ids: list[int],
        error: str,
        error_stack: str | None = None,
    ) -> PaymentRetry:
        """
        Create retry record for failed payment.

        Args:
            user_id: User ID
            amount: Payment amount
            payment_type: REFERRAL_EARNING or DEPOSIT_REWARD
            earning_ids: IDs of earnings/rewards to pay
            error: Error message
            error_stack: Error stack trace (optional)

        Returns:
            PaymentRetry record
        """
        logger.info(
            f"Creating retry record for user {user_id}, "
            f"amount: {amount} USDT",
            extra={
                "payment_type": payment_type.value,
                "earning_ids": earning_ids,
            },
        )

        # Check if retry already exists for the SAME earning_ids
        existing = await self.retry_repo.find_by(
            user_id=user_id,
            payment_type=payment_type.value,
            resolved=False,
        )

        # Filter to find exact match by earning_ids
        matching_retry = None
        if existing:
            for retry_record in existing:
                # Check if earning_ids match (same payment)
                if set(retry_record.earning_ids) == set(earning_ids):
                    matching_retry = retry_record
                    break

        if matching_retry:
            # Update existing record for the same payment
            retry = matching_retry
            logger.info(
                f"Found existing retry record {retry.id} "
                f"for same earning_ids: {earning_ids}"
            )
            await self.retry_repo.update(
                retry.id,
                amount=amount,
                last_error=error,
                error_stack=error_stack,
            )
            logger.info(
                f"Updated existing retry record {retry.id}"
            )
        else:
            # Create new retry record
            next_retry_at = self._calculate_next_retry_time(0)

            retry = await self.retry_repo.create(
                user_id=user_id,
                amount=amount,
                payment_type=payment_type.value,
                earning_ids=earning_ids,
                attempt_count=0,
                max_retries=DEFAULT_MAX_RETRIES,
                next_retry_at=next_retry_at,
                last_error=error,
                error_stack=error_stack,
                in_dlq=False,
                resolved=False,
            )

            logger.info(
                f"Created new retry record {retry.id}, "
                f"next retry at: {next_retry_at.isoformat()}"
            )

        await self.session.commit()
        return retry

    def _calculate_next_retry_time(
        self, attempt_count: int
    ) -> datetime:
        """
        Calculate next retry time using exponential backoff.

        Formula: delay = BASE_DELAY * 2^attempt_count
        Example: 1min, 2min, 4min, 8min, 16min

        Args:
            attempt_count: Current attempt count

        Returns:
            Next retry datetime
        """
        delay_minutes = BASE_RETRY_DELAY_MINUTES * (2 ** attempt_count)
        return datetime.now(UTC) + timedelta(minutes=delay_minutes)
