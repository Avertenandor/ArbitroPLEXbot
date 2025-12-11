"""
Activity formatter for monitoring service.

This module provides formatting utilities for user activity statistics
and AI conversation reports to be consumed by ARIA AI assistant.
"""

from loguru import logger

from ..utils import HAS_ACTIVITY


class ActivityFormatter:
    """
    Formats user activity data and AI conversations for ARIA assistant.

    All methods create separate database sessions to avoid transaction conflicts
    with the main monitoring service operations.
    """

    @staticmethod
    async def format_for_aria(hours: int = 24) -> str:
        """
        Format activity statistics for ARIA assistant.

        Creates a separate session to avoid transaction conflicts with main operations.
        Delegates formatting to UserActivityService for detailed statistics.

        Args:
            hours: Lookback period in hours (default: 24)

        Returns:
            Formatted text report with activity statistics, or error message if:
            - Activity logging is not activated
            - An error occurs during data retrieval

        Example:
            >>> report = await ActivityFormatter.format_for_aria(hours=48)
            >>> print(report)
            📊 Статистика активности за последние 48 часов
            ...
        """
        if not HAS_ACTIVITY:
            return "📊 Система логирования активности не активирована."

        try:
            # Use separate session to avoid polluting main transaction
            from app.config.database import async_session_maker
            from app.services.user_activity_service import UserActivityService

            async with async_session_maker() as activity_session:
                service = UserActivityService(activity_session)
                return await service.format_stats_for_aria(hours)
        except Exception as e:
            logger.error(f"Error formatting activity for ARIA: {e}")
            return "⚠️ Ошибка получения статистики активности"

    @staticmethod
    async def get_ai_conversations_report(hours: int = 24) -> str:
        """
        Get AI conversations report for ARIA assistant.

        Creates a separate session to avoid transaction conflicts with main operations.
        Retrieves and formats recent AI conversation history for context and analysis.

        Args:
            hours: Lookback period in hours (default: 24)

        Returns:
            Formatted text with recent AI conversations, or error message if:
            - Conversation logging is not activated
            - An error occurs during data retrieval

        Example:
            >>> report = await ActivityFormatter.get_ai_conversations_report(hours=12)
            >>> print(report)
            🤖 Разговоры с AI за последние 12 часов
            ...
        """
        if not HAS_ACTIVITY:
            return "📊 Логирование разговоров не активировано."

        try:
            # Use separate session to avoid polluting main transaction
            from app.config.database import async_session_maker
            from app.services.user_activity_service import UserActivityService

            async with async_session_maker() as ai_session:
                service = UserActivityService(ai_session)
                return await service.format_ai_conversations_for_aria(hours)
        except Exception as e:
            logger.error(f"Error getting AI conversations for ARIA: {e}")
            return "⚠️ Ошибка получения разговоров с AI"
