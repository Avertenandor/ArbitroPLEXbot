"""
Payment Retry Service - Statistics Module.

Module: stats.py
Provides statistics and user-specific retry operations.
"""


from app.models.payment_retry import PaymentRetry


class RetryStatsManager:
    """Retry statistics management."""

    def __init__(self, retry_repo, session) -> None:
        """Initialize stats manager."""
        self.retry_repo = retry_repo
        self.session = session

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
