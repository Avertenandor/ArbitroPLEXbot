"""
Payment Retry Service - Main Module.

This module provides payment retry functionality with exponential backoff
and Dead Letter Queue (DLQ) management.

Module Structure:
- constants.py: Configuration constants
- core.py: Main service class and retry record creation
- processor.py: Batch and individual retry processing
- payment_handler.py: Payment execution logic
- dlq_manager.py: Dead Letter Queue operations
- stats.py: Statistics and user retry operations

Public Interface:
- PaymentRetryService: Main service class (backward compatible)
"""

from sqlalchemy.ext.asyncio import AsyncSession

from .core import PaymentRetryCore
from .dlq_manager import DLQManager
from .processor import PaymentRetryProcessor
from .stats import RetryStatsManager


class PaymentRetryService:
    """
    Payment retry service with exponential backoff and DLQ.

    This is the main service class that provides backward compatibility
    with the original monolithic implementation.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize payment retry service."""
        self.session = session

        # Initialize all components
        self.core = PaymentRetryCore(session)
        self.processor = PaymentRetryProcessor(self.core)
        self.dlq_manager = DLQManager(self.core.retry_repo, session)
        self.stats_manager = RetryStatsManager(self.core.retry_repo, session)

        # Expose repositories for backward compatibility
        self.retry_repo = self.core.retry_repo
        self.earning_repo = self.core.earning_repo
        self.reward_repo = self.core.reward_repo
        self.transaction_repo = self.core.transaction_repo

    # Delegate methods to appropriate components for backward compatibility

    async def create_retry_record(self, *args, **kwargs):
        """Create retry record for failed payment."""
        return await self.core.create_retry_record(*args, **kwargs)

    async def process_pending_retries(self, blockchain_service) -> dict:
        """Process all pending retries."""
        return await self.processor.process_pending_retries(blockchain_service)

    async def get_dlq_items(self):
        """Get all DLQ items (for admin review)."""
        return await self.dlq_manager.get_dlq_items()

    async def retry_dlq_item(self, retry_id: int, blockchain_service):
        """Manually retry DLQ item (admin action)."""
        return await self.dlq_manager.retry_dlq_item(
            retry_id, blockchain_service, self.core
        )

    async def get_retry_stats(self):
        """Get retry statistics."""
        return await self.stats_manager.get_retry_stats()

    async def get_user_retries(self, user_id: int):
        """Get pending retries for specific user."""
        return await self.stats_manager.get_user_retries(user_id)


# Re-export for backward compatibility
__all__ = ['PaymentRetryService']
