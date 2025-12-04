"""
Payment retry service (PART5 critical).

Exponential backoff retry mechanism for failed payments.
Prevents user fund loss from transient failures.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TransactionStatus, TransactionType
from app.models.payment_retry import PaymentRetry, PaymentType
from app.repositories.deposit_reward_repository import (
    DepositRewardRepository,
)
from app.repositories.payment_retry_repository import (
    PaymentRetryRepository,
)
from app.repositories.referral_earning_repository import (
    ReferralEarningRepository,
)
from app.repositories.transaction_repository import TransactionRepository

# Exponential backoff: 1min, 2min, 4min, 8min, 16min
BASE_RETRY_DELAY_MINUTES = 1
DEFAULT_MAX_RETRIES = 5


class PaymentRetryService:
    """Payment retry service with exponential backoff and DLQ."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize payment retry service."""
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

    async def process_pending_retries(
        self, blockchain_service
    ) -> dict:
        """
        Process all pending retries.

        Called by background job (e.g., every minute).

        Args:
            blockchain_service: Blockchain service for sending payments

        Returns:
            Dict with processed, successful, failed, moved_to_dlq counts
        """
        pending = await self.retry_repo.get_pending_retries()

        if not pending:
            return self._create_empty_stats()

        logger.info(
            f"Processing {len(pending)} pending payment retries..."
        )

        stats = self._process_retry_batch(pending, blockchain_service)

        logger.info(
            f"Retry processing complete: {stats['successful']} successful, "
            f"{stats['failed']} failed, {stats['moved_to_dlq']} moved to DLQ "
            f"out of {stats['processed']} total"
        )

        return stats

    async def _process_retry_batch(
        self, pending: list[PaymentRetry], blockchain_service
    ) -> dict:
        """Process a batch of pending retries and collect statistics."""
        stats = {
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "moved_to_dlq": 0,
        }

        for retry in pending:
            result = await self._process_single_retry_safe(
                retry, blockchain_service
            )
            stats["processed"] += 1
            stats[result] += 1

        return stats

    async def _process_single_retry_safe(
        self, retry: PaymentRetry, blockchain_service
    ) -> str:
        """
        Process a single retry with error handling.

        Returns:
            One of: 'successful', 'failed', 'moved_to_dlq'
        """
        try:
            result = await self._process_retry(retry, blockchain_service)
            if result["success"]:
                return "successful"
            if result["moved_to_dlq"]:
                return "moved_to_dlq"
            return "failed"
        except Exception as e:
            logger.error(f"Error processing retry {retry.id}: {e}")
            return "failed"

    def _create_empty_stats(self) -> dict:
        """Create empty statistics dict."""
        return {
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "moved_to_dlq": 0,
        }

    async def _process_retry(
        self, retry: PaymentRetry, blockchain_service
    ) -> dict:
        """
        Process single retry attempt.

        Args:
            retry: PaymentRetry record
            blockchain_service: Blockchain service

        Returns:
            Dict with success and moved_to_dlq flags
        """
        logger.info(
            f"Processing retry {retry.id} for user {retry.user_id}, "
            f"attempt {retry.attempt_count + 1}/{retry.max_retries}"
        )

        await self._increment_retry_attempt(retry)

        try:
            user = await self._load_and_validate_user(retry)
            payment_result = await self._execute_payment(
                retry, user, blockchain_service
            )
            await self._save_payment_tx_hash(retry, payment_result)
            self._validate_payment_result(payment_result)

            return await self._handle_payment_success(
                retry, user, payment_result["tx_hash"]
            )

        except Exception as e:
            return await self._handle_payment_failure(retry, e)

    async def _increment_retry_attempt(
        self, retry: PaymentRetry
    ) -> None:
        """Increment the retry attempt count."""
        await self.retry_repo.update(
            retry.id,
            attempt_count=retry.attempt_count + 1,
            last_attempt_at=datetime.now(UTC),
        )

    async def _load_and_validate_user(self, retry: PaymentRetry):
        """Load user and validate wallet address."""
        user_stmt = select(retry.user)
        user_result = await self.session.execute(user_stmt)
        user = user_result.scalar_one()

        if not user.wallet_address:
            raise ValueError(
                f"User {user.telegram_id} has no wallet address"
            )

        return user

    async def _execute_payment(
        self, retry: PaymentRetry, user, blockchain_service
    ) -> dict:
        """Execute the blockchain payment."""
        logger.info(
            f"Attempting payment: {retry.amount} USDT "
            f"to {user.wallet_address}"
        )

        previous_tx_hash = retry.tx_hash if retry.tx_hash else None
        if previous_tx_hash:
            logger.info(
                f"Previous tx_hash found: {previous_tx_hash} - "
                f"will check before sending new transaction"
            )

        return await blockchain_service.send_payment(
            user.wallet_address,
            retry.amount,
            previous_tx_hash=previous_tx_hash,
        )

    async def _save_payment_tx_hash(
        self, retry: PaymentRetry, payment_result: dict
    ) -> None:
        """Save transaction hash if present and changed."""
        tx_hash = payment_result.get("tx_hash")
        if tx_hash and tx_hash != retry.tx_hash:
            await self.retry_repo.update(retry.id, tx_hash=tx_hash)
            await self.session.flush()

    def _validate_payment_result(self, payment_result: dict) -> None:
        """Validate payment result and raise error if unsuccessful."""
        if not payment_result["success"]:
            if payment_result.get("status") == "pending":
                logger.info(
                    f"Transaction {payment_result['tx_hash']} pending - "
                    f"will check again on next retry"
                )
                raise ValueError(
                    payment_result.get("error", "Transaction pending")
                )
            raise ValueError(
                payment_result.get("error", "Unknown payment error")
            )

    async def _handle_payment_success(
        self, retry: PaymentRetry, user, tx_hash: str
    ) -> dict:
        """Handle successful payment."""
        logger.info(
            f"Payment retry {retry.id} succeeded! TxHash: {tx_hash}"
        )

        await self.retry_repo.update(
            retry.id, resolved=True, tx_hash=tx_hash
        )

        await self._mark_earnings_as_paid(retry, tx_hash)
        await self._create_transaction_record(retry, user, tx_hash)

        await self.session.commit()

        logger.info(
            "Payment retry succeeded",
            extra={
                "retry_id": retry.id,
                "attempt_count": retry.attempt_count,
                "tx_hash": tx_hash,
            },
        )

        return {"success": True, "moved_to_dlq": False}

    async def _mark_earnings_as_paid(
        self, retry: PaymentRetry, tx_hash: str
    ) -> None:
        """Mark earnings or rewards as paid."""
        if retry.payment_type == PaymentType.REFERRAL_EARNING.value:
            await self._mark_referral_earnings_paid(
                retry.earning_ids, tx_hash
            )
        elif retry.payment_type == PaymentType.DEPOSIT_REWARD.value:
            await self._mark_deposit_rewards_paid(
                retry.earning_ids, tx_hash
            )

    async def _mark_referral_earnings_paid(
        self, earning_ids: list[int], tx_hash: str
    ) -> None:
        """Mark referral earnings as paid."""
        for earning_id in earning_ids:
            await self.earning_repo.update(
                earning_id, paid=True, tx_hash=tx_hash
            )

    async def _mark_deposit_rewards_paid(
        self, reward_ids: list[int], tx_hash: str
    ) -> None:
        """Mark deposit rewards as paid."""
        for reward_id in reward_ids:
            await self.reward_repo.update(
                reward_id,
                paid=True,
                paid_at=datetime.now(UTC),
                tx_hash=tx_hash,
            )

    async def _create_transaction_record(
        self, retry: PaymentRetry, user, tx_hash: str
    ) -> None:
        """Create transaction record for on-chain payout."""
        tx_type = self._get_transaction_type(retry.payment_type)

        await self.transaction_repo.create(
            user_id=retry.user_id,
            tx_hash=tx_hash,
            type=tx_type.value,
            amount=retry.amount,
            to_address=user.wallet_address,
            status=TransactionStatus.CONFIRMED.value,
        )

    def _get_transaction_type(
        self, payment_type: str
    ) -> TransactionType:
        """Get transaction type based on payment type."""
        if payment_type == PaymentType.REFERRAL_EARNING.value:
            return TransactionType.REFERRAL_REWARD
        return TransactionType.SYSTEM_PAYOUT

    async def _handle_payment_failure(
        self, retry: PaymentRetry, error: Exception
    ) -> dict:
        """Handle payment failure."""
        error_msg = str(error)
        logger.error(
            f"Retry {retry.id} attempt "
            f"{retry.attempt_count} failed: {error_msg}"
        )

        await self.retry_repo.update(retry.id, last_error=error_msg)

        if retry.attempt_count >= retry.max_retries:
            return await self._move_to_dlq(retry)

        return await self._schedule_next_retry(retry)

    async def _move_to_dlq(self, retry: PaymentRetry) -> dict:
        """Move retry to dead letter queue."""
        await self.retry_repo.update(
            retry.id, in_dlq=True, next_retry_at=None
        )

        logger.warning(
            f"Retry {retry.id} moved to DLQ "
            f"after {retry.attempt_count} attempts"
        )

        await self.session.commit()
        return {"success": False, "moved_to_dlq": True}

    async def _schedule_next_retry(self, retry: PaymentRetry) -> dict:
        """Schedule next retry with exponential backoff."""
        next_retry = self._calculate_next_retry_time(retry.attempt_count)

        await self.retry_repo.update(retry.id, next_retry_at=next_retry)

        logger.info(
            f"Retry {retry.id} scheduled for next attempt "
            f"at: {next_retry.isoformat()}"
        )

        await self.session.commit()
        return {"success": False, "moved_to_dlq": False}

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

    async def get_dlq_items(self) -> list[PaymentRetry]:
        """
        Get all DLQ items (for admin review).

        Returns:
            List of DLQ payment retries
        """
        return await self.retry_repo.get_dlq_entries()

    async def retry_dlq_item(
        self, retry_id: int, blockchain_service
    ) -> tuple[bool, str | None, str | None]:
        """
        Manually retry DLQ item (admin action).

        Args:
            retry_id: Retry ID
            blockchain_service: Blockchain service

        Returns:
            Tuple of (success, tx_hash, error_message)
        """
        retry = await self.retry_repo.get_by_id(retry_id)

        if not retry:
            return False, None, "Retry record not found"

        if retry.resolved:
            return False, None, "Payment already resolved"

        logger.info(
            f"Manual retry of DLQ item {retry_id} by admin"
        )

        # Remove from DLQ and reset
        await self.retry_repo.update(
            retry_id,
            in_dlq=False,
            attempt_count=0,
            next_retry_at=datetime.now(UTC),
        )

        await self.session.flush()

        # Process the retry
        result = await self._process_retry(retry, blockchain_service)

        if result["success"]:
            return True, retry.tx_hash, None
        else:
            return False, None, retry.last_error or "Retry failed"

    async def get_retry_stats(self) -> dict:
        """
        Get retry statistics.

        Returns:
            Dict with comprehensive retry stats
        """
        # Get counts using SQL COUNT to avoid loading all records
        pending = await self.retry_repo.count(
            resolved=False, in_dlq=False
        )
        # Keep as is - get_dlq_entries may have complex logic
        dlq = len(await self.retry_repo.get_dlq_entries())
        resolved = await self.retry_repo.count(resolved=True)

        # Get amounts
        all_unresolved = await self.retry_repo.find_by(resolved=False)
        total_amount = sum(r.amount for r in all_unresolved)

        dlq_items = await self.retry_repo.get_dlq_entries()
        dlq_amount = sum(r.amount for r in dlq_items)

        return {
            "pending_retries": pending,
            "dlq_items": dlq,
            "resolved_retries": resolved,
            "total_amount": total_amount,
            "dlq_amount": dlq_amount,
        }

    async def get_user_retries(
        self, user_id: int
    ) -> list[PaymentRetry]:
        """
        Get pending retries for specific user.

        Args:
            user_id: User ID

        Returns:
            List of user's pending retries
        """
        return await self.retry_repo.find_by(
            user_id=user_id, resolved=False
        )
