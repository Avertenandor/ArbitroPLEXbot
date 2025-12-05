"""
Payment Retry Service - Processor Module.

Module: processor.py
Handles batch and individual retry processing.
Processes pending retries with exponential backoff.
"""

from datetime import UTC, datetime
from loguru import logger

from app.models.payment_retry import PaymentRetry


class PaymentRetryProcessor:
    """Retry processing logic."""

    def __init__(self, retry_core) -> None:
        """Initialize processor with core components."""
        self.retry_core = retry_core
        self.retry_repo = retry_core.retry_repo
        self.session = retry_core.session

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

        stats = await self._process_retry_batch(pending, blockchain_service)

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
            # Import here to avoid circular dependency
            from .payment_handler import PaymentRetryHandler

            handler = PaymentRetryHandler(self.retry_core, self.retry_repo, self.session)
            result = await handler.process_retry(retry, blockchain_service)

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
