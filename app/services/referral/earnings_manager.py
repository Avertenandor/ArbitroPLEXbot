"""
Referral earnings management module.

Handles earnings operations including pending earnings retrieval and payment marking.
"""

from decimal import Decimal

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.referral_earning import ReferralEarning
from app.repositories.referral_earning_repository import (
    ReferralEarningRepository,
)
from app.repositories.referral_repository import ReferralRepository


class ReferralEarningsManager:
    """Manages referral earnings operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize earnings manager."""
        self.session = session
        self.referral_repo = ReferralRepository(session)
        self.earning_repo = ReferralEarningRepository(session)

    async def get_pending_earnings(
        self, user_id: int, page: int = 1, limit: int = 10
    ) -> dict:
        """
        Get pending (unpaid) earnings for user.

        Uses SQL aggregation to avoid OOM on large datasets.

        Args:
            user_id: User ID
            page: Page number
            limit: Items per page

        Returns:
            Dict with earnings, total, total_amount, page, pages
        """
        # Get user's referral relationships
        relationships = await self.referral_repo.find_by(
            referrer_id=user_id
        )
        relationship_ids = [r.id for r in relationships]

        if not relationship_ids:
            return {
                "earnings": [],
                "total": 0,
                "total_amount": Decimal("0"),
                "page": 1,
                "pages": 0,
            }

        offset = (page - 1) * limit

        # Get unpaid earnings with pagination
        earnings = await self.earning_repo.get_unpaid_by_referral_ids(
            relationship_ids, limit=limit, offset=offset
        )

        # Use SQL aggregation for count and sum
        stats_stmt = select(
            func.count(ReferralEarning.id).label('total'),
            func.sum(ReferralEarning.amount).label('total_amount')
        ).where(
            ReferralEarning.referral_id.in_(relationship_ids),
            ReferralEarning.paid == False  # noqa: E712
        )

        stats_result = await self.session.execute(stats_stmt)
        stats = stats_result.one()

        total = stats.total or 0
        total_amount = stats.total_amount or Decimal("0")
        pages = (total + limit - 1) // limit if total > 0 else 0

        return {
            "earnings": earnings,
            "total": total,
            "total_amount": total_amount,
            "page": page,
            "pages": pages,
        }

    async def mark_earning_as_paid(
        self, earning_id: int, tx_hash: str
    ) -> tuple[bool, str | None]:
        """
        Mark earning as paid (called by payment processor).

        Args:
            earning_id: Earning ID
            tx_hash: Transaction hash

        Returns:
            Tuple of (success, error_message)
        """
        earning = await self.earning_repo.get_by_id(earning_id)

        if not earning:
            return False, "Earning not found"

        if earning.paid:
            return False, "Already paid"

        await self.earning_repo.update(
            earning_id, paid=True, tx_hash=tx_hash
        )

        await self.session.commit()

        logger.info(
            "Earning marked as paid",
            extra={
                "earning_id": earning_id,
                "amount": str(earning.amount),
                "tx_hash": tx_hash,
            },
        )

        return True, None
