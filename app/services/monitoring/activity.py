"""
Activity monitoring module for ARIA AI Assistant.

Provides user inquiries statistics, activity analytics, and user journey tracking.
"""

from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin
from app.models.user import User

from .utils import (
    DATE_FORMAT_SHORT,
    HAS_ACTIVITY,
    HAS_INQUIRIES,
    FormatHelper,
    validate_limit,
)

# Try to import optional models
if HAS_INQUIRIES:
    try:
        from app.models.user_inquiry import UserInquiry
    except ImportError:
        HAS_INQUIRIES = False


class ActivityMonitor:
    """
    Monitor for user activity and inquiries.

    Provides statistics on user inquiries, activity analytics,
    and individual user journey tracking.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize activity monitor.

        Args:
            session: Async database session
        """
        self.session = session

    async def get_inquiries_stats(self, limit: int = 20) -> dict[str, Any]:
        """
        Get user inquiries/questions statistics.

        Retrieves comprehensive statistics about user inquiries including:
        - Total count and breakdown by status
        - Recent inquiries with user and admin information
        - Question text (truncated to 100 characters)

        Args:
            limit: Maximum number of recent inquiries to return (default: 20)

        Returns:
            Dict containing:
            - available (bool): Whether inquiries module is installed
            - total (int): Total number of inquiries
            - by_status (dict): Count of inquiries grouped by status
            - new_count (int): Count of new inquiries
            - in_progress_count (int): Count of in-progress inquiries
            - closed_count (int): Count of closed inquiries
            - recent (list): List of recent inquiries with details
            - message (str): Error or unavailability message (if applicable)
            - error (str): Error message if something went wrong
        """
        if not HAS_INQUIRIES:
            return {
                "available": False,
                "message": "Inquiries module not installed",
            }

        try:
            # Validate limit parameter
            limit = validate_limit(limit, max_value=100, default=20)

            # Total inquiries
            total_result = await self.session.execute(
                select(func.count(UserInquiry.id))
            )
            total = total_result.scalar() or 0

            # By status
            status_result = await self.session.execute(
                select(
                    UserInquiry.status,
                    func.count(UserInquiry.id),
                ).group_by(UserInquiry.status)
            )
            by_status = {row[0]: row[1] for row in status_result.fetchall()}

            # Recent inquiries with User and Admin information
            recent_result = await self.session.execute(
                select(
                    UserInquiry.id,
                    UserInquiry.initial_question,
                    UserInquiry.status,
                    UserInquiry.created_at,
                    User.username,
                    Admin.username.label("admin_username"),
                )
                .join(User, UserInquiry.user_id == User.id)
                .outerjoin(Admin, UserInquiry.assigned_admin_id == Admin.id)
                .order_by(UserInquiry.created_at.desc())
                .limit(limit)
            )

            recent = []
            for row in recent_result.fetchall():
                inquiry_id = row[0]
                question = row[1]
                status = row[2]
                created_at = row[3]
                username = row[4]
                admin_username = row[5]

                # Truncate question text to 100 characters
                truncated_question = FormatHelper.truncate_text(
                    question, max_length=100
                )

                # Format date
                formatted_date = FormatHelper.format_datetime(
                    created_at, fmt=DATE_FORMAT_SHORT
                )

                recent.append({
                    "id": inquiry_id,
                    "question": truncated_question,
                    "status": status,
                    "created": formatted_date,
                    "user": username or "Unknown",
                    "assigned_to": admin_username or "Не назначен",
                })

            return {
                "available": True,
                "total": total,
                "by_status": by_status,
                "new_count": by_status.get("new", 0),
                "in_progress_count": by_status.get("in_progress", 0),
                "closed_count": by_status.get("closed", 0),
                "recent": recent,
            }

        except Exception as e:
            logger.error(f"Error getting inquiries stats: {e}")
            return {
                "available": True,
                "error": str(e),
            }

    async def get_analytics(self, hours: int = 24) -> dict[str, Any]:
        """
        Get comprehensive user activity analytics.

        Retrieves detailed activity statistics including funnel metrics,
        conversion rates, and activity breakdown by type. Delegates to
        UserActivityService for actual data collection.

        Args:
            hours: Lookback period in hours (default: 24)

        Returns:
            Dict containing:
            - period_hours (int): Lookback period used
            - funnel (dict): Registration funnel metrics
            - conversions (dict): Conversion rates between funnel stages
            - activity_by_type (dict): Activity counts grouped by type
            - total_actions (int): Total number of actions
            - unique_users (int): Number of unique users
            - hourly (list): Hourly activity breakdown
            - error (str): Error message if activity tracking unavailable

        Raises:
            Returns error dict if activity tracking is not available
            or if UserActivityService fails to import
        """
        if not HAS_ACTIVITY:
            return {
                "error": "Activity tracking not available",
            }

        try:
            from app.services.user_activity_service import UserActivityService

            service = UserActivityService(self.session)
            return await service.get_comprehensive_stats(hours)

        except ImportError as e:
            logger.error(f"Failed to import UserActivityService: {e}")
            return {
                "error": "UserActivityService not available",
            }
        except Exception as e:
            logger.error(f"Error getting activity analytics: {e}")
            return {
                "error": str(e),
            }

    async def get_user_journey(self, telegram_id: int) -> list[dict[str, Any]]:
        """
        Get complete journey of a specific user.

        Retrieves chronological list of all activities performed by a user,
        including timestamps, activity types, descriptions, and messages.
        Delegates to UserActivityService for data collection.

        Args:
            telegram_id: User's Telegram ID

        Returns:
            List of activity dicts, each containing:
            - time (str): Formatted timestamp
            - type (str): Activity type
            - emoji (str): Emoji representation of activity type
            - description (str): Human-readable description
            - message (str): Message text (truncated to 100 chars) if applicable

            Returns empty list if activity tracking is not available
            or if user has no recorded activities

        Note:
            Gracefully handles ImportError and returns empty list
            if UserActivityService is not available.
        """
        if not HAS_ACTIVITY:
            return []

        try:
            from app.services.user_activity_service import UserActivityService

            service = UserActivityService(self.session)
            return await service.get_user_journey(telegram_id)

        except ImportError as e:
            logger.error(f"Failed to import UserActivityService: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting user journey: {e}")
            return []
