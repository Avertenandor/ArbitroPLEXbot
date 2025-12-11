"""
Admin monitoring module.

Provides monitoring and statistics for admin activities, actions, and sessions.
"""

from typing import Any

from loguru import logger
from sqlalchemy import case, distinct, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin
from app.models.admin_action import AdminAction
from app.models.admin_session import AdminSession
from app.services.monitoring.utils import (
    DEFAULT_LOOKBACK_HOURS,
    DEFAULT_USERNAME,
    LIMIT_TOP_ACTIONS,
    MAX_LIMIT_ADMIN_ACTIONS,
    DATE_FORMAT_TIME,
    FormatHelper,
    TimeHelper,
    validate_limit,
)


class AdminMonitor:
    """
    Monitor for admin activities and statistics.

    Provides optimized queries for admin metrics, actions, and session tracking.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize admin monitor.

        Args:
            session: Async database session
        """
        self.session = session

    async def get_stats(self, hours: int = DEFAULT_LOOKBACK_HOURS) -> dict[str, Any]:
        """
        Get comprehensive admin activity statistics.

        Uses optimized query with CASE statements to combine multiple COUNT
        operations into a single database query for better performance.

        Args:
            hours: Lookback period in hours (default: 24)

        Returns:
            Dict containing:
                - total_admins: Total number of admins
                - active_admins_last_hours: Active admins in period
                - hours_period: Lookback period used
                - total_actions: Total actions in period
                - top_action_types: List of top action types with counts
                - admins_list: List of all admins with roles and status

        Example:
            >>> monitor = AdminMonitor(session)
            >>> stats = await monitor.get_stats(hours=24)
            >>> print(f"Active admins: {stats['active_admins_last_hours']}")
        """
        try:
            since = TimeHelper.get_since(hours)
            logger.debug(f"AdminMonitor: Getting admin stats, since={since}")

            # Optimized query: Combine multiple COUNT queries using CASE statements
            # This reduces database round trips from 3 to 1 for basic counts
            counts_query = select(
                func.count(Admin.id).label("total_admins"),
                func.count(
                    distinct(
                        case(
                            (
                                (AdminSession.is_active == True) & (AdminSession.last_activity >= since),  # noqa: E712
                                AdminSession.admin_id,
                            ),
                            else_=None,
                        )
                    )
                ).label("active_admins"),
                func.count(case((AdminAction.created_at >= since, AdminAction.id), else_=None)).label(
                    "total_actions"
                ),
            ).select_from(Admin).outerjoin(AdminSession, AdminSession.admin_id == Admin.id).outerjoin(
                AdminAction, AdminAction.admin_id == Admin.id
            )

            counts_result = await self.session.execute(counts_query)
            counts_row = counts_result.fetchone()

            total_admins = counts_row[0] if counts_row else 0
            active_admins = counts_row[1] if counts_row else 0
            total_actions = counts_row[2] if counts_row else 0

            logger.debug(
                f"AdminMonitor: total_admins={total_admins}, "
                f"active_admins={active_admins}, "
                f"total_actions={total_actions}"
            )

            # Top actions by type (separate query as it requires GROUP BY)
            top_actions_result = await self.session.execute(
                select(AdminAction.action_type, func.count(AdminAction.id).label("count"))
                .where(AdminAction.created_at >= since)
                .group_by(AdminAction.action_type)
                .order_by(text("count DESC"))
                .limit(LIMIT_TOP_ACTIONS)
            )
            top_actions = [
                {"type": row[0], "count": row[1]} for row in top_actions_result.fetchall()
            ]

            # Get admin list with their roles and status
            admins_result = await self.session.execute(
                select(Admin.username, Admin.role, Admin.is_blocked).order_by(Admin.role)
            )
            admins_list = [
                {
                    "username": FormatHelper.safe_username(row[0]),
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

    async def get_recent_actions(
        self,
        limit: int = 10,
        hours: int = DEFAULT_LOOKBACK_HOURS,
    ) -> list[dict[str, Any]]:
        """
        Get recent admin actions log with details.

        Retrieves the most recent admin actions within the specified time period,
        including action type, description, timestamp, and performing admin.

        Args:
            limit: Maximum number of actions to return (default: 10)
            hours: Lookback period in hours (default: 24)

        Returns:
            List of action dicts containing:
                - type: Action type
                - description: Action description (extracted from details)
                - time: Formatted time string (HH:MM)
                - admin: Username of admin who performed the action

        Example:
            >>> monitor = AdminMonitor(session)
            >>> actions = await monitor.get_recent_actions(limit=5, hours=24)
            >>> for action in actions:
            ...     print(f"{action['time']} - {action['admin']}: {action['type']}")
        """
        try:
            # Validate limit to prevent excessive queries
            validated_limit = validate_limit(limit, default=10, max_value=MAX_LIMIT_ADMIN_ACTIONS)
            since = TimeHelper.get_since(hours)

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
                .limit(validated_limit)
            )

            actions = []
            for row in result.fetchall():
                # Extract description from details JSON object
                details = row[1] or {}
                description = ""

                if isinstance(details, dict):
                    # Try common keys for description
                    description = details.get("description", details.get("action", ""))
                elif details:
                    # Fallback: convert to string and truncate
                    description = str(details)[:100]

                actions.append(
                    {
                        "type": row[0],
                        "description": FormatHelper.truncate_text(description, max_length=100, suffix=""),
                        "time": FormatHelper.format_datetime(row[2], fmt=DATE_FORMAT_TIME),
                        "admin": FormatHelper.safe_username(row[3]),
                    }
                )

            logger.debug(f"AdminMonitor: Retrieved {len(actions)} recent actions")
            return actions

        except Exception as e:
            logger.error(f"Error getting recent admin actions: {e}")
            return []
