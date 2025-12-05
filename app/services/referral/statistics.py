"""
Referral statistics module.

Handles all statistics-related operations for referrals including leaderboards,
activity stats, conversion stats, and platform-wide statistics.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deposit import Deposit
from app.models.referral import Referral
from app.models.referral_earning import ReferralEarning
from app.repositories.referral_earning_repository import (
    ReferralEarningRepository,
)
from app.repositories.referral_repository import ReferralRepository


class ReferralStatisticsManager:
    """Manages referral statistics and analytics."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize statistics manager."""
        self.session = session
        self.referral_repo = ReferralRepository(session)
        self.earning_repo = ReferralEarningRepository(session)

    async def get_referral_stats(self, user_id: int) -> dict:
        """
        Get referral statistics for user.

        Args:
            user_id: User ID

        Returns:
            Dict with referral counts and earnings
        """
        # Get all referral relationships
        all_relationships = await self.referral_repo.find_by(
            referrer_id=user_id
        )

        # Count by level
        direct_referrals = sum(1 for r in all_relationships if r.level == 1)
        level2_referrals = sum(1 for r in all_relationships if r.level == 2)
        level3_referrals = sum(1 for r in all_relationships if r.level == 3)

        # Calculate earnings
        relationship_ids = [r.id for r in all_relationships]

        if relationship_ids:
            all_earnings = await self.earning_repo.find_by_referral_ids(
                relationship_ids
            )
            total_earned = sum(e.amount for e in all_earnings)
            paid_earnings = sum(e.amount for e in all_earnings if e.paid)
            pending_earnings = sum(
                e.amount for e in all_earnings if not e.paid
            )
        else:
            total_earned = Decimal("0")
            paid_earnings = Decimal("0")
            pending_earnings = Decimal("0")

        return {
            "direct_referrals": direct_referrals,
            "level2_referrals": level2_referrals,
            "level3_referrals": level3_referrals,
            "total_earned": total_earned,
            "pending_earnings": pending_earnings,
            "paid_earnings": paid_earnings,
        }

    async def get_referral_leaderboard(self, limit: int = 10) -> dict:
        """
        Get referral leaderboard.

        Args:
            limit: Number of top users to return

        Returns:
            Dict with by_referrals and by_earnings lists
        """
        # Get all users with referrals
        stmt = text("""
            WITH referral_stats AS (
                SELECT
                    r.referrer_id,
                    COUNT(DISTINCT r.referral_id) as referral_count,
                    COALESCE(SUM(re.amount), 0) as total_earnings
                FROM referrals r
                LEFT JOIN referral_earnings re ON re.referral_id = r.id
                GROUP BY r.referrer_id
            )
            SELECT
                u.id as user_id,
                u.telegram_id,
                u.username,
                rs.referral_count,
                rs.total_earnings
            FROM referral_stats rs
            JOIN users u ON u.id = rs.referrer_id
            ORDER BY rs.referral_count DESC, rs.total_earnings DESC
        """)

        result = await self.session.execute(stmt)
        rows = result.all()

        # Build by_referrals leaderboard
        by_referrals = []
        for idx, row in enumerate(rows[:limit], 1):
            by_referrals.append({
                "rank": idx,
                "user_id": row.user_id,
                "telegram_id": row.telegram_id,
                "username": row.username,
                "referral_count": row.referral_count,
                "total_earnings": Decimal(str(row.total_earnings)),
            })

        # Build by_earnings leaderboard (sorted differently)
        sorted_by_earnings = sorted(
            rows,
            key=lambda r: (r.total_earnings, r.referral_count),
            reverse=True
        )
        by_earnings = []
        for idx, row in enumerate(sorted_by_earnings[:limit], 1):
            by_earnings.append({
                "rank": idx,
                "user_id": row.user_id,
                "telegram_id": row.telegram_id,
                "username": row.username,
                "referral_count": row.referral_count,
                "total_earnings": Decimal(str(row.total_earnings)),
            })

        return {
            "by_referrals": by_referrals,
            "by_earnings": by_earnings,
        }

    async def get_user_leaderboard_position(self, user_id: int) -> dict:
        """
        Get user's position in leaderboard.

        Args:
            user_id: User ID

        Returns:
            Dict with referral_rank, earnings_rank, total_users
        """
        # Get all users with referrals
        stmt = text("""
            WITH referral_stats AS (
                SELECT
                    r.referrer_id,
                    COUNT(DISTINCT r.referral_id) as referral_count,
                    COALESCE(SUM(re.amount), 0) as total_earnings
                FROM referrals r
                LEFT JOIN referral_earnings re ON re.referral_id = r.id
                GROUP BY r.referrer_id
            )
            SELECT
                referrer_id,
                referral_count,
                total_earnings,
                RANK() OVER (ORDER BY referral_count DESC,
                             total_earnings DESC) as referral_rank,
                RANK() OVER (ORDER BY total_earnings DESC,
                             referral_count DESC) as earnings_rank
            FROM referral_stats
        """)

        result = await self.session.execute(stmt)
        rows = result.all()

        # Find user's position
        referral_rank = None
        earnings_rank = None

        for row in rows:
            if row.referrer_id == user_id:
                referral_rank = row.referral_rank
                earnings_rank = row.earnings_rank
                break

        return {
            "referral_rank": referral_rank,
            "earnings_rank": earnings_rank,
            "total_users": len(rows),
        }

    async def get_platform_referral_stats(self) -> dict:
        """
        Get platform-wide referral statistics.

        Uses SQL aggregation to avoid OOM on large datasets.

        Returns:
            Dict with total referrals, earnings breakdown
        """
        # Aggregate referral stats by level using SQL
        referral_stats_stmt = select(
            Referral.level,
            func.count(Referral.id).label('count'),
            func.sum(Referral.total_earned).label('earnings')
        ).group_by(Referral.level)

        referral_result = await self.session.execute(referral_stats_stmt)
        referral_rows = referral_result.all()

        # Build by_level dict
        by_level = {}
        total_referrals = 0
        for row in referral_rows:
            by_level[row.level] = {
                "count": row.count or 0,
                "earnings": row.earnings or Decimal("0"),
            }
            total_referrals += row.count or 0

        # Ensure all levels are present
        for level in [1, 2, 3]:
            if level not in by_level:
                by_level[level] = {"count": 0, "earnings": Decimal("0")}

        # Aggregate earning stats using SQL
        earning_stats_stmt = select(
            func.sum(ReferralEarning.amount).label('total_earnings'),
            func.sum(
                func.case((ReferralEarning.paid == True, ReferralEarning.amount), else_=0)  # noqa: E712
            ).label('paid_earnings'),
            func.sum(
                func.case((ReferralEarning.paid == False, ReferralEarning.amount), else_=0)  # noqa: E712
            ).label('pending_earnings')
        )

        earning_result = await self.session.execute(earning_stats_stmt)
        earning_stats = earning_result.one()

        return {
            "total_referrals": total_referrals,
            "total_earnings": earning_stats.total_earnings or Decimal("0"),
            "paid_earnings": earning_stats.paid_earnings or Decimal("0"),
            "pending_earnings": earning_stats.pending_earnings or Decimal("0"),
            "by_level": by_level,
        }

    async def get_daily_earnings_stats(
        self, user_id: int, days: int = 7
    ) -> dict:
        """
        Get daily earnings statistics for user.

        Args:
            user_id: User ID
            days: Number of days to retrieve (default 7)

        Returns:
            Dict with daily earnings breakdown
        """
        # Get user's referral relationships
        relationships = await self.referral_repo.find_by(referrer_id=user_id)
        relationship_ids = [r.id for r in relationships]

        if not relationship_ids:
            return {
                "daily_stats": [],
                "total_period": Decimal("0"),
                "today_earned": Decimal("0"),
                "average_daily": Decimal("0"),
            }

        # Calculate date range
        now = datetime.now(UTC)
        start_date = now - timedelta(days=days)

        # Get daily aggregated earnings
        stmt = text("""
            SELECT
                DATE(re.created_at AT TIME ZONE 'UTC') as earn_date,
                SUM(re.amount) as daily_amount,
                COUNT(*) as transactions_count
            FROM referral_earnings re
            WHERE re.referral_id = ANY(:ref_ids)
              AND re.created_at >= :start_date
            GROUP BY DATE(re.created_at AT TIME ZONE 'UTC')
            ORDER BY earn_date DESC
        """)

        result = await self.session.execute(
            stmt,
            {"ref_ids": relationship_ids, "start_date": start_date}
        )
        rows = result.all()

        daily_stats = []
        total_period = Decimal("0")
        today_earned = Decimal("0")
        today = now.date()

        for row in rows:
            amount = Decimal(str(row.daily_amount)) if row.daily_amount else Decimal("0")
            daily_stats.append({
                "date": row.earn_date,
                "amount": amount,
                "count": row.transactions_count or 0,
            })
            total_period += amount
            if row.earn_date == today:
                today_earned = amount

        average_daily = total_period / Decimal(days) if days > 0 else Decimal("0")

        return {
            "daily_stats": daily_stats,
            "total_period": total_period,
            "today_earned": today_earned,
            "average_daily": average_daily,
            "days": days,
        }

    async def get_referral_conversion_stats(self, user_id: int) -> dict:
        """
        Get referral conversion statistics.

        Shows how many referrals made deposits and average deposit amount.

        Args:
            user_id: User ID

        Returns:
            Dict with conversion stats
        """
        # Get direct referrals (level 1)
        direct_referrals = await self.referral_repo.find_by(
            referrer_id=user_id, level=1
        )

        if not direct_referrals:
            return {
                "total_referrals": 0,
                "referrals_with_deposits": 0,
                "conversion_rate": Decimal("0"),
                "total_deposits_amount": Decimal("0"),
                "average_deposit": Decimal("0"),
            }

        referral_user_ids = [r.referral_id for r in direct_referrals]

        # Count referrals with deposits
        deposit_stats_stmt = select(
            func.count(func.distinct(Deposit.user_id)).label('users_with_deposits'),
            func.sum(Deposit.amount).label('total_deposits'),
            func.count(Deposit.id).label('total_deposit_count')
        ).where(
            Deposit.user_id.in_(referral_user_ids),
            Deposit.status == 'confirmed'
        )

        result = await self.session.execute(deposit_stats_stmt)
        stats = result.one()

        total_referrals = len(direct_referrals)
        referrals_with_deposits = stats.users_with_deposits or 0
        total_deposits = stats.total_deposits or Decimal("0")
        deposit_count = stats.total_deposit_count or 0

        conversion_rate = (
            Decimal(referrals_with_deposits) / Decimal(total_referrals) * 100
            if total_referrals > 0 else Decimal("0")
        )
        average_deposit = (
            total_deposits / Decimal(deposit_count)
            if deposit_count > 0 else Decimal("0")
        )

        return {
            "total_referrals": total_referrals,
            "referrals_with_deposits": referrals_with_deposits,
            "conversion_rate": conversion_rate,
            "total_deposits_amount": total_deposits,
            "average_deposit": average_deposit,
            "deposit_count": deposit_count,
        }

    async def get_referral_activity_stats(self, user_id: int) -> dict:
        """
        Get referral activity statistics.

        Shows active vs inactive referrals.

        Args:
            user_id: User ID

        Returns:
            Dict with activity stats
        """
        now = datetime.now(UTC)
        thirty_days_ago = now - timedelta(days=30)

        # Get all referrals (all levels)
        all_referrals = await self.referral_repo.find_by(referrer_id=user_id)

        if not all_referrals:
            return {
                "total_referrals": 0,
                "active_referrals": 0,
                "inactive_referrals": 0,
                "activity_rate": Decimal("0"),
                "by_level": {
                    1: {"total": 0, "active": 0},
                    2: {"total": 0, "active": 0},
                    3: {"total": 0, "active": 0},
                },
            }

        referral_user_ids = [r.referral_id for r in all_referrals]

        # Get users with recent deposits (active)
        active_stmt = select(
            func.distinct(Deposit.user_id)
        ).where(
            Deposit.user_id.in_(referral_user_ids),
            Deposit.created_at >= thirty_days_ago,
            Deposit.status == 'confirmed'
        )

        result = await self.session.execute(active_stmt)
        active_user_ids = set(row[0] for row in result.all())

        # Calculate stats by level
        by_level = {
            1: {"total": 0, "active": 0},
            2: {"total": 0, "active": 0},
            3: {"total": 0, "active": 0},
        }
        for ref in all_referrals:
            if ref.level in by_level:
                by_level[ref.level]["total"] += 1
                if ref.referral_id in active_user_ids:
                    by_level[ref.level]["active"] += 1

        total_referrals = len(all_referrals)
        active_referrals = len(active_user_ids)
        inactive_referrals = total_referrals - active_referrals
        activity_rate = (
            Decimal(active_referrals) / Decimal(total_referrals) * 100
            if total_referrals > 0 else Decimal("0")
        )

        return {
            "total_referrals": total_referrals,
            "active_referrals": active_referrals,
            "inactive_referrals": inactive_referrals,
            "activity_rate": activity_rate,
            "by_level": by_level,
        }
