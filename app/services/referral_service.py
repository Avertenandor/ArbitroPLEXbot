"""
Referral service.

Manages referral chains, relationships, and reward processing.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.referral import Referral
from app.models.user import User
from app.repositories.referral_earning_repository import (
    ReferralEarningRepository,
)
from app.repositories.referral_repository import ReferralRepository
from app.repositories.user_repository import UserRepository
from app.services.base_service import BaseService
from app.services.referral.referral_reward_processor import (
    ReferralRewardProcessor,
)

if TYPE_CHECKING:
    from aiogram import Bot

# Referral system configuration (from PART2 docs)
# 3-level referral program: 5% from deposits AND earnings at each level
REFERRAL_DEPTH = 3
REFERRAL_RATES = {
    1: Decimal("0.05"),  # 5% for level 1 (direct referrals)
    2: Decimal("0.05"),  # 5% for level 2
    3: Decimal("0.05"),  # 5% for level 3
}


class ReferralService(BaseService):
    """Referral service for managing referral chains and rewards."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize referral service."""
        super().__init__(session)
        self.referral_repo = ReferralRepository(session)
        self.earning_repo = ReferralEarningRepository(session)
        self.user_repo = UserRepository(session)
        self.reward_processor = ReferralRewardProcessor(session)

    async def get_referral_chain(
        self, user_id: int, depth: int = REFERRAL_DEPTH
    ) -> list[User]:
        """
        Get referral chain (PostgreSQL CTE optimized).

        Uses recursive CTE to efficiently fetch entire referral chain.

        Args:
            user_id: User ID
            depth: Chain depth to retrieve

        Returns:
            List of users from direct referrer to Nth level
        """
        # Use PostgreSQL recursive CTE for efficient chain retrieval
        query = text("""
            WITH RECURSIVE referral_chain AS (
                -- Base case: start with the user
                SELECT
                    u.id,
                    u.telegram_id,
                    u.username,
                    u.wallet_address,
                    u.referrer_id,
                    u.created_at,
                    u.updated_at,
                    u.is_verified,
                    u.earnings_blocked,
                    u.financial_password,
                    0 AS level
                FROM users u
                WHERE u.id = :user_id

                UNION ALL

                -- Recursive case: get referrer of previous level
                SELECT
                    u.id,
                    u.telegram_id,
                    u.username,
                    u.wallet_address,
                    u.referrer_id,
                    u.created_at,
                    u.updated_at,
                    u.is_verified,
                    u.earnings_blocked,
                    u.financial_password,
                    rc.level + 1 AS level
                FROM users u
                INNER JOIN referral_chain rc ON u.id = rc.referrer_id
                WHERE rc.level < :depth
            )
            SELECT *
            FROM referral_chain
            WHERE level > 0
            ORDER BY level ASC
        """)

        result = await self.session.execute(
            query, {"user_id": user_id, "depth": depth}
        )
        rows = result.all()

        # Map rows to User objects
        chain = []
        for row in rows:
            user = User(
                id=row.id,
                telegram_id=row.telegram_id,
                username=row.username,
                wallet_address=row.wallet_address,
                referrer_id=row.referrer_id,
                is_verified=row.is_verified,
                earnings_blocked=row.earnings_blocked,
                financial_password=row.financial_password,
            )
            user.created_at = row.created_at
            user.updated_at = row.updated_at
            chain.append(user)

        logger.debug(
            "Referral chain retrieved",
            extra={
                "user_id": user_id,
                "depth": depth,
                "chain_length": len(chain)
            },
        )

        return chain

    async def create_referral_relationships(
        self, new_user_id: int, direct_referrer_id: int
    ) -> tuple[bool, str | None]:
        """
        Create referral relationships for new user.

        Creates multi-level referral chain (up to REFERRAL_DEPTH levels).

        Args:
            new_user_id: New user ID
            direct_referrer_id: Direct referrer ID

        Returns:
            Tuple of (success, error_message)
        """
        # Self-referral check
        if new_user_id == direct_referrer_id:
            return False, "Нельзя пригласить самого себя"

        # Get direct referrer
        stmt = select(User).where(User.id == direct_referrer_id)
        result = await self.session.execute(stmt)
        direct_referrer = result.scalar_one_or_none()

        if not direct_referrer:
            return False, "Реферер не найден"

        # Get referral chain from direct referrer
        referrers = await self.get_referral_chain(
            direct_referrer_id, REFERRAL_DEPTH
        )

        # Add direct referrer as level 1
        referrers.insert(0, direct_referrer)

        # Check for referral loops
        referrer_ids = [r.id for r in referrers]
        if new_user_id in referrer_ids:
            logger.warning(
                "Referral loop detected",
                extra={
                    "new_user_id": new_user_id,
                    "direct_referrer_id": direct_referrer_id,
                    "chain_ids": referrer_ids,
                },
            )
            return False, "Нельзя создать циклическую реферальную цепочку"

        # Create referral records for each level
        for i, referrer in enumerate(referrers[: REFERRAL_DEPTH]):
            level = i + 1

            # Check if relationship already exists
            existing = await self.referral_repo.find_by(
                referrer_id=referrer.id, referral_id=new_user_id
            )

            if not existing:
                await self.referral_repo.create(
                    referrer_id=referrer.id,
                    referral_id=new_user_id,
                    level=level,
                    total_earned=Decimal("0"),
                )

                logger.debug(
                    "Referral relationship created",
                    extra={
                        "referrer_id": referrer.id,
                        "referral_id": new_user_id,
                        "level": level,
                    },
                )

        await self.session.commit()

        logger.info(
            "Referral chain created",
            extra={
                "new_user_id": new_user_id,
                "direct_referrer_id": direct_referrer_id,
                "levels_created": min(len(referrers), REFERRAL_DEPTH),
            },
        )

        return True, None

    async def process_referral_rewards(
        self, user_id: int, deposit_amount: Decimal, bot: "Bot | None" = None
    ) -> tuple[bool, Decimal, str | None]:
        """
        Process referral rewards for a deposit.

        Creates earning records for all referrers in chain.

        Args:
            user_id: User who made deposit
            deposit_amount: Deposit amount
            bot: Optional bot instance for sending notifications

        Returns:
            Tuple of (success, total_rewards, error_message)
        """
        result = await self.reward_processor.process_rewards(
            user_id=user_id,
            amount=deposit_amount,
            reward_type="deposit",
        )

        # Send notifications if bot provided
        if bot and result.notifications:
            await self._send_reward_notifications(bot, result.notifications)

        return result.success, result.total_rewards, result.error_message

    async def process_roi_referral_rewards(
        self, user_id: int, roi_amount: Decimal, bot: "Bot | None" = None
    ) -> tuple[bool, Decimal, str | None]:
        """
        Process referral rewards for ROI accrual.

        Args:
            user_id: User who received ROI
            roi_amount: ROI amount
            bot: Optional bot instance for sending notifications

        Returns:
            Tuple of (success, total_rewards, error_message)
        """
        result = await self.reward_processor.process_rewards(
            user_id=user_id,
            amount=roi_amount,
            reward_type="roi",
        )

        # Send notifications if bot provided (only for significant amounts)
        if bot and result.notifications:
            # Filter small ROI notifications to avoid spam
            significant = [n for n in result.notifications if n.reward_amount >= 0.01]
            if significant:
                await self._send_reward_notifications(bot, significant)

        return result.success, result.total_rewards, result.error_message

    async def _send_reward_notifications(
        self, bot: "Bot", notifications: list
    ) -> None:
        """Send reward notifications to referrers."""
        from app.services.referral.referral_notifications import (
            notify_referral_reward,
        )

        for notif in notifications:
            try:
                await notify_referral_reward(
                    bot=bot,
                    referrer_telegram_id=notif.referrer_telegram_id,
                    reward_amount=notif.reward_amount,
                    level=notif.level,
                    source_username=notif.source_username,
                    source_telegram_id=notif.source_telegram_id,
                    reward_type=notif.reward_type,
                )
            except Exception as e:
                logger.warning(f"Failed to send reward notification: {e}")

    async def get_referrals_by_level(
        self, user_id: int, level: int, page: int = 1, limit: int = 10
    ) -> dict:
        """
        Get user's referrals by level.

        Args:
            user_id: User ID
            level: Referral level (1-3)
            page: Page number
            limit: Items per page

        Returns:
            Dict with referrals, total, page, pages
        """
        offset = (page - 1) * limit

        # Get referrals with pagination, eager load referral users to avoid N+1
        stmt = (
            select(Referral)
            .options(selectinload(Referral.referral))
            .where(Referral.referrer_id == user_id, Referral.level == level)
            .order_by(Referral.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(stmt)
        relationships = list(result.scalars().all())

        # Get total count using SQL COUNT (avoid loading all records)
        count_stmt = select(func.count(Referral.id)).where(
            Referral.referrer_id == user_id, Referral.level == level
        )
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Build referrals list (users already loaded via eager loading)
        referrals = []
        for rel in relationships:
            user = rel.referral  # Already loaded via selectinload

            if user:
                referrals.append({
                    "user": user,
                    "earned": rel.total_earned,
                    "joined_at": rel.created_at,
                })

        pages = (total + limit - 1) // limit

        return {
            "referrals": referrals,
            "total": total,
            "page": page,
            "pages": pages,
        }

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
        from app.models.referral_earning import ReferralEarning

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
        from app.models.referral_earning import ReferralEarning

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
        from datetime import timedelta

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
        from app.models.deposit import Deposit

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
        from datetime import timedelta

        from app.models.deposit import Deposit

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

    async def get_my_referrers(self, user_id: int) -> dict:
        """
        Get who invited this user (their referrer chain).

        Shows the user's position in the referral structure.

        Args:
            user_id: User ID

        Returns:
            Dict with referrer info
        """
        # Get all relationships where this user is the referral
        stmt = (
            select(Referral)
            .options(selectinload(Referral.referrer))
            .where(Referral.referral_id == user_id)
            .order_by(Referral.level)
        )

        result = await self.session.execute(stmt)
        relationships = list(result.scalars().all())

        if not relationships:
            return {
                "has_referrer": False,
                "referrers": [],
                "direct_referrer": None,
            }

        referrers = []
        direct_referrer = None

        for rel in relationships:
            referrer_user = rel.referrer
            if referrer_user:
                referrer_info = {
                    "level": rel.level,
                    "user_id": referrer_user.id,
                    "telegram_id": referrer_user.telegram_id,
                    "username": referrer_user.username,
                    "you_earned_them": rel.total_earned,
                }
                referrers.append(referrer_info)

                if rel.level == 1:
                    direct_referrer = referrer_info

        return {
            "has_referrer": bool(direct_referrer),
            "referrers": referrers,
            "direct_referrer": direct_referrer,
        }
