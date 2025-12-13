"""Admin statistics module for MonitoringService."""

from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin
from app.models.admin_action import AdminAction
from app.models.admin_session import AdminSession


class AdminStatsService:
    """Service for collecting admin activity statistics."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize admin stats service."""
        self.session = session

    async def get_admin_stats(self, hours: int = 24) -> dict[str, Any]:
        """
        Get admin activity statistics.

        Args:
            hours: Lookback period in hours

        Returns:
            Dict with admin statistics
        """
        try:
            since = datetime.now(UTC) - timedelta(hours=hours)
            logger.debug(f"AdminStatsService: Getting stats, since={since}")

            # Total admins
            total_result = await self.session.execute(
                select(func.count(Admin.id))
            )
            total_admins = total_result.scalar() or 0
            logger.debug(f"AdminStatsService: total_admins={total_admins}")

            # Active admins (have session in last N hours)
            active_result = await self.session.execute(
                select(func.count(func.distinct(AdminSession.admin_id)))
                .where(AdminSession.last_activity >= since)
                .where(AdminSession.is_active == True)  # noqa: E712
            )
            active_admins = active_result.scalar() or 0

            # Admin actions count
            actions_result = await self.session.execute(
                select(func.count(AdminAction.id))
                .where(AdminAction.created_at >= since)
            )
            total_actions = actions_result.scalar() or 0

            # Top actions by type
            top_actions_result = await self.session.execute(
                select(
                    AdminAction.action_type,
                    func.count(AdminAction.id).label("count"),
                )
                .where(AdminAction.created_at >= since)
                .group_by(AdminAction.action_type)
                .order_by(text("count DESC"))
                .limit(5)
            )
            top_actions = [
                {"type": row[0], "count": row[1]}
                for row in top_actions_result.fetchall()
            ]

            # Get admin list with their roles
            admins_result = await self.session.execute(
                select(Admin.username, Admin.role, Admin.is_blocked)
                .order_by(Admin.role)
            )
            admins_list = [
                {
                    "username": row[0] or "Unknown",
                    "role": row[1],
                    "blocked": row[2],
                }
                for row in admins_result.fetchall()
            ]

            return {
                "total_admins": total_admins,
                "active_admins_last_hours": active_admins,
                "hours_period": hours,
                "total_actions": total_actions,
                "top_action_types": top_actions,
                "admins_list": admins_list,
            }
        except Exception as e:
            logger.error(f"Error getting admin stats: {e}")
            return {"error": str(e)}

    async def get_recent_admin_actions(
        self, limit: int = 10, hours: int = 24
    ) -> list[dict[str, Any]]:
        """
        Get recent admin actions log.

        Args:
            limit: Max number of actions
            hours: Lookback period

        Returns:
            List of recent actions
        """
        try:
            since = datetime.now(UTC) - timedelta(hours=hours)

            result = await self.session.execute(
                select(
                    AdminAction.action_type,
                    AdminAction.details,
                    AdminAction.created_at,
                    Admin.username,
                )
                .join(Admin, AdminAction.admin_id == Admin.id)
                .where(AdminAction.created_at >= since)
                .order_by(AdminAction.created_at.desc())
                .limit(limit)
            )

            actions = []
            for row in result.fetchall():
                # details is JSON, extract description if available
                details = row[1] or {}
                desc = ""
                if isinstance(details, dict):
                    desc = details.get(
                        "description", details.get("action", "")
                    )
                elif details:
                    desc = str(details)[:100]
                actions.append(
                    {
                        "type": row[0],
                        "description": desc[:100] if desc else "",
                        "time": row[2].strftime("%H:%M") if row[2] else "",
                        "admin": row[3] or "Unknown",
                    }
                )

            return actions
        except Exception as e:
            logger.error(f"Error getting recent actions: {e}")
            return []
