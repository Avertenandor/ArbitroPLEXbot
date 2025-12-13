"""
User Activity Service - Maintenance Module.

Methods for maintaining and cleaning up activity records.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import text


class UserActivityMaintenanceMixin:
    """Mixin with maintenance and cleanup methods."""

    async def cleanup_old_records(self) -> int:
        """
        Delete records older than RETENTION_DAYS.

        Returns:
            Number of deleted records
        """
        try:
            cutoff = datetime.now(UTC) - timedelta(
                days=self.RETENTION_DAYS
            )
            result = await self.session.execute(
                text(
                    "DELETE FROM user_activities "
                    "WHERE created_at < :cutoff"
                ),
                {"cutoff": cutoff},
            )
            deleted = result.rowcount or 0
            if deleted > 0:
                logger.info(
                    f"Cleaned up {deleted} old activity records"
                )
            return deleted
        except Exception as e:
            logger.error(f"Failed to cleanup old records: {e}")
            return 0

    async def enforce_max_records(self) -> int:
        """
        Delete oldest records if total exceeds MAX_RECORDS.

        Returns:
            Number of deleted records
        """
        try:
            # Count total records
            count_result = await self.session.execute(
                text("SELECT COUNT(*) FROM user_activities")
            )
            total = count_result.scalar() or 0

            if total <= self.MAX_RECORDS:
                return 0

            # Delete oldest records
            to_delete = total - self.MAX_RECORDS
            result = await self.session.execute(
                text(
                    """
                    DELETE FROM user_activities
                    WHERE id IN (
                        SELECT id FROM user_activities
                        ORDER BY created_at ASC
                        LIMIT :limit
                    )
                """
                ),
                {"limit": to_delete},
            )
            deleted = result.rowcount or 0
            if deleted > 0:
                logger.info(
                    f"Enforced max records limit: "
                    f"deleted {deleted} oldest records"
                )
            return deleted
        except Exception as e:
            logger.error(f"Failed to enforce max records: {e}")
            return 0

    async def get_stats(self) -> dict[str, Any]:
        """
        Get activity logging statistics.

        Returns:
            Dict with stats: total, oldest, newest, by_type
        """
        try:
            # Total count
            count_result = await self.session.execute(
                text("SELECT COUNT(*) FROM user_activities")
            )
            total = count_result.scalar() or 0

            # Oldest and newest
            range_result = await self.session.execute(
                text(
                    """
                    SELECT MIN(created_at), MAX(created_at)
                    FROM user_activities
                """
                )
            )
            row = range_result.fetchone()
            oldest = row[0] if row else None
            newest = row[1] if row else None

            # By type
            type_result = await self.session.execute(
                text(
                    """
                    SELECT activity_type, COUNT(*) as cnt
                    FROM user_activities
                    GROUP BY activity_type
                    ORDER BY cnt DESC
                """
                )
            )
            by_type = {row[0]: row[1] for row in type_result.fetchall()}

            return {
                "total": total,
                "max_records": self.MAX_RECORDS,
                "retention_days": self.RETENTION_DAYS,
                "oldest": oldest.isoformat() if oldest else None,
                "newest": newest.isoformat() if newest else None,
                "by_type": by_type,
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}
