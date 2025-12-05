"""
Payment Retry Service - Payment Handler Module.

Module: payment_handler.py
Handles payment execution, success, and failure logic.
Manages transaction execution and state updates.
"""

from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import select

from app.models.enums import TransactionStatus, TransactionType
from app.models.payment_retry import PaymentRetry, PaymentType


class PaymentRetryHandler:
    """Payment execution and handling."""

    def __init__(self, retry_core, retry_repo, session) -> None:
        """Initialize handler with core components."""
        self.retry_core = retry_core
        self.retry_repo = retry_repo
        self.session = session
        self.earning_repo = retry_core.earning_repo
        self.reward_repo = retry_core.reward_repo
        self.transaction_repo = retry_core.transaction_repo

    async def process_retry(
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
            # Import here to avoid circular dependency
            from .dlq_manager import DLQManager
            dlq_manager = DLQManager(self.retry_repo, self.session)
            return await dlq_manager.move_to_dlq(retry)

        return await self._schedule_next_retry(retry)

    async def _schedule_next_retry(self, retry: PaymentRetry) -> dict:
        """Schedule next retry with exponential backoff."""
        next_retry = self.retry_core._calculate_next_retry_time(retry.attempt_count)

        await self.retry_repo.update(retry.id, next_retry_at=next_retry)

        logger.info(
            f"Retry {retry.id} scheduled for next attempt "
            f"at: {next_retry.isoformat()}"
        )

        await self.session.commit()
        return {"success": False, "moved_to_dlq": False}
