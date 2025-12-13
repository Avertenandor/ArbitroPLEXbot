"""User activity analytics module for MonitoringService."""

from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession


# Try to import optional models
try:
    from app.models.user_activity import UserActivity  # noqa: F401

    HAS_ACTIVITY = True
except ImportError:
    HAS_ACTIVITY = False


class ActivityService:
    """Service for collecting user activity analytics."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize activity service."""
        self.session = session

    async def get_activity_analytics(
        self,
        hours: int = 24,
    ) -> dict[str, Any]:
        """
        Get comprehensive user activity analytics for ARIA.

        Args:
            hours: Lookback period

        Returns:
            Dict with activity statistics, funnel, conversions
        """
        if not HAS_ACTIVITY:
            return {"error": "Activity tracking not available"}

        try:
            from app.services.user_activity_service import (
                UserActivityService,
            )

            service = UserActivityService(self.session)
            return await service.get_comprehensive_stats(hours)
        except Exception as e:
            logger.error(f"Error getting activity analytics: {e}")
            return {"error": str(e)}

    async def get_user_journey(
        self,
        telegram_id: int,
    ) -> list[dict[str, Any]]:
        """
        Get complete journey of a specific user.

        Args:
            telegram_id: User's Telegram ID

        Returns:
            List of user activities in chronological order
        """
        if not HAS_ACTIVITY:
            return []

        try:
            from app.services.user_activity_service import (
                UserActivityService,
            )

            service = UserActivityService(self.session)
            return await service.get_user_journey(telegram_id)
        except Exception as e:
            logger.error(f"Error getting user journey: {e}")
            return []

    async def format_activity_for_aria(
        self,
        hours: int = 24,
    ) -> str:
        """
        Format activity statistics for ARIA assistant.
        Uses separate session to avoid transaction conflicts.

        Args:
            hours: Lookback period

        Returns:
            Formatted text report
        """
        if not HAS_ACTIVITY:
            msg = "📊 Система логирования активности "
            msg += "не активирована."
            return msg

        try:
            # Use separate session to avoid polluting main transaction
            from app.config.database import async_session_maker
            from app.services.user_activity_service import (
                UserActivityService,
            )

            async with async_session_maker() as activity_session:
                service = UserActivityService(activity_session)
                return await service.format_stats_for_aria(hours)
        except Exception as e:
            logger.error(f"Error formatting activity: {e}")
            return (
                "⚠️ Ошибка получения статистики активности"
            )

    async def get_ai_conversations_report(
        self,
        hours: int = 24,
    ) -> str:
        """
        Get AI conversations report for ARIA.
        Uses separate session to avoid transaction conflicts.

        Args:
            hours: Lookback period

        Returns:
            Formatted text with recent conversations
        """
        if not HAS_ACTIVITY:
            return "📊 Логирование разговоров не активировано."

        try:
            # Use separate session to avoid polluting main transaction
            from app.config.database import async_session_maker
            from app.services.user_activity_service import (
                UserActivityService,
            )

            async with async_session_maker() as ai_session:
                service = UserActivityService(ai_session)
                return await service.format_ai_conversations_for_aria(hours)
        except Exception as e:
            logger.error(f"Error getting AI conversations: {e}")
            return "⚠️ Ошибка получения разговоров с AI"
