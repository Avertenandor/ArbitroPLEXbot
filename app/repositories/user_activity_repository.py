"""
User Activity Repository.

Data access layer for user activity tracking.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_activity import ActivityType, UserActivity
from app.repositories.base import BaseRepository


class UserActivityRepository(BaseRepository[UserActivity]):
    """Repository for user activity operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository."""
        super().__init__(UserActivity, session)

    async def log_activity(
        self,
        telegram_id: int,
        activity_type: str,
        user_id: int | None = None,
        description: str | None = None,
        message_text: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UserActivity:
        """
        Log a user activity.

        Args:
            telegram_id: User's Telegram ID
            activity_type: Type of activity (from ActivityType)
            user_id: Internal user ID (if known)
            description: Human-readable description
            message_text: Full message text (if applicable)
            metadata: Additional JSON data

        Returns:
            Created UserActivity record
        """
        activity = UserActivity(
            telegram_id=telegram_id,
            user_id=user_id,
            activity_type=activity_type,
            description=description,
            message_text=message_text[:1000] if message_text else None,
            metadata=metadata,
            created_at=datetime.now(UTC),
        )
        self.session.add(activity)
        return activity

    async def get_user_activities(
        self,
        telegram_id: int | None = None,
        user_id: int | None = None,
        activity_type: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[UserActivity]:
        """
        Get user activities with filters.

        Args:
            telegram_id: Filter by Telegram ID
            user_id: Filter by user ID
            activity_type: Filter by activity type
            since: Filter by date (after)
            limit: Max results

        Returns:
            List of activities
        """
        conditions = []

        if telegram_id is not None:
            conditions.append(UserActivity.telegram_id == telegram_id)
        if user_id is not None:
            conditions.append(UserActivity.user_id == user_id)
        if activity_type is not None:
            conditions.append(UserActivity.activity_type == activity_type)
        if since is not None:
            conditions.append(UserActivity.created_at >= since)

        query = (
            select(UserActivity)
            .where(and_(*conditions) if conditions else True)
            .order_by(UserActivity.created_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_type(
        self,
        activity_type: str,
        since: datetime | None = None,
    ) -> int:
        """Count activities by type."""
        conditions = [UserActivity.activity_type == activity_type]
        if since:
            conditions.append(UserActivity.created_at >= since)

        query = select(func.count(UserActivity.id)).where(and_(*conditions))
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def count_unique_users_by_type(
        self,
        activity_type: str,
        since: datetime | None = None,
    ) -> int:
        """Count unique users by activity type."""
        conditions = [UserActivity.activity_type == activity_type]
        if since:
            conditions.append(UserActivity.created_at >= since)

        query = select(
            func.count(func.distinct(UserActivity.telegram_id))
        ).where(and_(*conditions))
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_activity_stats(
        self,
        hours: int = 24,
    ) -> dict[str, Any]:
        """
        Get comprehensive activity statistics.

        Args:
            hours: Lookback period

        Returns:
            Dict with activity counts by type
        """
        since = datetime.now(UTC) - timedelta(hours=hours)

        # Count by type
        query = (
            select(
                UserActivity.activity_type,
                func.count(UserActivity.id).label("count"),
                func.count(func.distinct(UserActivity.telegram_id)).label("unique_users"),
            )
            .where(UserActivity.created_at >= since)
            .group_by(UserActivity.activity_type)
        )

        result = await self.session.execute(query)
        rows = result.all()

        stats = {
            "period_hours": hours,
            "activities": {},
            "total_actions": 0,
            "total_unique_users": 0,
        }

        for row in rows:
            stats["activities"][row.activity_type] = {
                "count": row.count,
                "unique_users": row.unique_users,
            }
            stats["total_actions"] += row.count

        # Get total unique users for period
        unique_query = select(
            func.count(func.distinct(UserActivity.telegram_id))
        ).where(UserActivity.created_at >= since)
        unique_result = await self.session.execute(unique_query)
        stats["total_unique_users"] = unique_result.scalar() or 0

        return stats

    async def get_user_journey(
        self,
        telegram_id: int,
        limit: int = 50,
    ) -> list[UserActivity]:
        """
        Get complete user journey (all activities).

        Args:
            telegram_id: User's Telegram ID
            limit: Max activities

        Returns:
            List of activities in chronological order
        """
        query = (
            select(UserActivity)
            .where(UserActivity.telegram_id == telegram_id)
            .order_by(UserActivity.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_funnel_stats(
        self,
        hours: int = 24,
    ) -> dict[str, int]:
        """
        Get registration funnel statistics.

        Returns counts for each step:
        1. Started bot
        2. Entered wallet
        3. Verified (PLEX paid)
        4. Made first deposit

        Args:
            hours: Lookback period

        Returns:
            Dict with funnel step counts
        """
        since = datetime.now(UTC) - timedelta(hours=hours)

        funnel = {
            "starts": await self.count_unique_users_by_type(ActivityType.START, since),
            "wallets_entered": await self.count_unique_users_by_type(
                ActivityType.WALLET_ENTERED, since
            ),
            "plex_paid": await self.count_unique_users_by_type(
                ActivityType.PLEX_PAID, since
            ),
            "first_deposits": await self.count_unique_users_by_type(
                ActivityType.DEPOSIT_CONFIRMED, since
            ),
        }

        return funnel

    async def get_hourly_activity(
        self,
        hours: int = 24,
    ) -> list[dict[str, Any]]:
        """
        Get activity grouped by hour.

        Args:
            hours: Lookback period

        Returns:
            List of hourly stats
        """
        since = datetime.now(UTC) - timedelta(hours=hours)

        query = (
            select(
                func.date_trunc("hour", UserActivity.created_at).label("hour"),
                func.count(UserActivity.id).label("count"),
                func.count(func.distinct(UserActivity.telegram_id)).label("users"),
            )
            .where(UserActivity.created_at >= since)
            .group_by(func.date_trunc("hour", UserActivity.created_at))
            .order_by(func.date_trunc("hour", UserActivity.created_at))
        )

        result = await self.session.execute(query)
        return [
            {"hour": row.hour, "count": row.count, "users": row.users}
            for row in result.all()
        ]

    async def cleanup_old_activities(
        self,
        days: int = 30,
    ) -> int:
        """
        Delete activities older than specified days.

        Args:
            days: Age threshold

        Returns:
            Number of deleted records
        """
        cutoff = datetime.now(UTC) - timedelta(days=days)
        stmt = delete(UserActivity).where(UserActivity.created_at < cutoff)
        result = await self.session.execute(stmt)
        return result.rowcount or 0
