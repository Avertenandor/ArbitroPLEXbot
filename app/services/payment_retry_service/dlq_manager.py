"""
Payment Retry Service - DLQ Manager Module.

Module: dlq_manager.py
Manages Dead Letter Queue (DLQ) operations.
Handles retries that have exhausted all attempts.
"""

from datetime import UTC, datetime

from loguru import logger

from app.models.payment_retry import PaymentRetry


class DLQManager:
    """Dead Letter Queue management."""

    def __init__(self, retry_repo, session) -> None:
        """Initialize DLQ manager."""
        self.retry_repo = retry_repo
        self.session = session

    async def move_to_dlq(self, retry: PaymentRetry) -> dict:
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

    async def get_dlq_items(self) -> list[PaymentRetry]:
        """
        Get all DLQ items (for admin review).

        Returns:
            List of DLQ payment retries
        """
        return await self.retry_repo.get_dlq_entries()

    async def retry_dlq_item(
        self, retry_id: int, blockchain_service, retry_core
    ) -> tuple[bool, str | None, str | None]:
        """
        Manually retry DLQ item (admin action).

        Args:
            retry_id: Retry ID
            blockchain_service: Blockchain service
            retry_core: PaymentRetryCore instance

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
        from .payment_handler import PaymentRetryHandler
        handler = PaymentRetryHandler(retry_core, self.retry_repo, self.session)
        result = await handler.process_retry(retry, blockchain_service)

        if result["success"]:
            return True, retry.tx_hash, None
        else:
            return False, None, retry.last_error or "Retry failed"
