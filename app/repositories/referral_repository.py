"""
Referral repository.

Data access layer for Referral model.
"""


from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.referral import Referral
from app.repositories.base import BaseRepository


class ReferralRepository(BaseRepository[Referral]):
    """Referral repository with specific queries."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize referral repository."""
        super().__init__(Referral, session)

    async def get_by_referrer(
        self, referrer_id: int, level: int | None = None
    ) -> list[Referral]:
        """
        Get referrals by referrer.

        Args:
            referrer_id: Referrer user ID
            level: Optional level filter (1-3)

        Returns:
            List of referrals
        """
        filters = {"referrer_id": referrer_id}
        if level:
            filters["level"] = level

        return await self.find_by(**filters)

    async def get_by_referral_user(
        self, referral_user_id: int
    ) -> list[Referral]:
        """
        Get referrals where user is the referral.

        Args:
            referral_user_id: Referral user ID

        Returns:
            List of referrals
        """
        return await self.find_by(
            referral_id=referral_user_id
        )

    async def get_level_1_referrals(
        self, referrer_id: int
    ) -> list[Referral]:
        """
        Get level 1 (direct) referrals.

        Args:
            referrer_id: Referrer user ID

        Returns:
            List of level 1 referrals
        """
        return await self.get_by_referrer(
            referrer_id=referrer_id, level=1
        )

    async def count_by_level(
        self, referrer_id: int, level: int
    ) -> int:
        """
        Count referrals by level.

        Args:
            referrer_id: Referrer user ID
            level: Referral level (1-3)

        Returns:
            Count of referrals
        """
        return await self.count(
            referrer_id=referrer_id, level=level
        )

    async def get_level_counts(
        self, referrer_id: int
    ) -> dict[int, int]:
        """
        Get referral counts for all levels in a single query.

        Optimized to avoid multiple COUNT queries - uses SQL GROUP BY.

        Args:
            referrer_id: Referrer user ID

        Returns:
            Dict mapping level to count {1: count1, 2: count2, 3: count3}
        """
        stmt = (
            select(
                Referral.level,
                func.count(Referral.id).label("count")
            )
            .where(Referral.referrer_id == referrer_id)
            .group_by(Referral.level)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        # Build result dict with all levels (default to 0)
        level_counts = {1: 0, 2: 0, 3: 0}
        for row in rows:
            level_counts[row.level] = row.count

        return level_counts

    async def get_referral_stats(
        self, referrer_id: int
    ) -> dict[int, dict[str, int | Decimal]]:
        """
        Get referral statistics grouped by level in a single query.

        Optimized to avoid fetching all records - uses SQL aggregation.

        Args:
            referrer_id: Referrer user ID

        Returns:
            Dict mapping level to stats {
                1: {"count": 5, "total_earned": Decimal("10.50")},
                2: {"count": 3, "total_earned": Decimal("5.25")},
                3: {"count": 1, "total_earned": Decimal("1.00")}
            }
        """
        stmt = (
            select(
                Referral.level,
                func.count(Referral.id).label("count"),
                func.coalesce(
                    func.sum(Referral.total_earned),
                    Decimal("0")
                ).label("total_earned")
            )
            .where(Referral.referrer_id == referrer_id)
            .group_by(Referral.level)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        # Build result dict with all levels (default to 0)
        stats = {
            1: {"count": 0, "total_earned": Decimal("0")},
            2: {"count": 0, "total_earned": Decimal("0")},
            3: {"count": 0, "total_earned": Decimal("0")},
        }

        for row in rows:
            stats[row.level] = {
                "count": row.count,
                "total_earned": row.total_earned,
            }

        return stats

    async def get_all_referral_ids(
        self, referrer_id: int
    ) -> list[int]:
        """
        Get all referral relationship IDs for a referrer.

        Optimized to avoid fetching full objects - only returns IDs.

        Args:
            referrer_id: Referrer user ID

        Returns:
            List of referral relationship IDs
        """
        stmt = (
            select(Referral.id)
            .where(Referral.referrer_id == referrer_id)
        )

        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def get_referral_user_ids_by_level(
        self, referrer_id: int, level: int
    ) -> list[int]:
        """
        Get user IDs of referrals at a specific level.

        Optimized to avoid fetching full objects - only returns user IDs.

        Args:
            referrer_id: Referrer user ID
            level: Referral level (1-3)

        Returns:
            List of referral user IDs
        """
        stmt = (
            select(Referral.referral_id)
            .where(
                Referral.referrer_id == referrer_id,
                Referral.level == level
            )
        )

        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]
