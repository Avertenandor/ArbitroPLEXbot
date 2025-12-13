"""
Monitoring Service for ARIA AI Assistant.

Provides real-time access to platform metrics, admin activity,
user statistics, financial data, and system health.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.monitoring.activity import ActivityService
from app.services.monitoring.admin_stats import AdminStatsService
from app.services.monitoring.financial_stats import FinancialStatsService
from app.services.monitoring.formatters import FormatterService
from app.services.monitoring.system_health import SystemHealthService
from app.services.monitoring.user_inquiries import UserInquiriesService
from app.services.monitoring.user_stats import UserStatsService


class MonitoringService:
    """
    Service for collecting platform metrics and statistics.

    Provides data for ARIA AI assistant to give real-time insights.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize monitoring service."""
        self.session = session

        # Initialize sub-services
        self.admin_stats = AdminStatsService(session)
        self.user_stats = UserStatsService(session)
        self.financial_stats = FinancialStatsService(session)
        self.system_health = SystemHealthService(session)
        self.user_inquiries = UserInquiriesService(session)
        self.activity = ActivityService(session)

    # Admin statistics methods
    async def get_admin_stats(self, hours: int = 24) -> dict[str, Any]:
        """
        Get admin activity statistics.

        Args:
            hours: Lookback period in hours

        Returns:
            Dict with admin statistics
        """
        return await self.admin_stats.get_admin_stats(hours)

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
        return await self.admin_stats.get_recent_admin_actions(
            limit, hours
        )

    # User statistics methods
    async def get_user_stats(self) -> dict[str, Any]:
        """
        Get user statistics.

        Returns:
            Dict with user statistics
        """
        return await self.user_stats.get_user_stats()

    async def get_user_full_history(
        self, identifier: str | int
    ) -> dict[str, Any]:
        """
        Get full history for a user by username, telegram_id, or user_id.

        Args:
            identifier: Username (with @), telegram_id, or user_id

        Returns:
            Dict with user's complete history
        """
        return await self.user_stats.get_user_full_history(identifier)

    async def search_users(
        self, query: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Search users by username, telegram_id, or wallet.

        Args:
            query: Search query
            limit: Max results

        Returns:
            List of matching users
        """
        return await self.user_stats.search_users(query, limit)

    # Financial statistics methods
    async def get_financial_stats(
        self, hours: int = 24
    ) -> dict[str, Any]:
        """
        Get financial statistics.

        Args:
            hours: Lookback period

        Returns:
            Dict with financial stats
        """
        return await self.financial_stats.get_financial_stats(hours)

    async def get_deposit_details(
        self, hours: int = 24
    ) -> dict[str, Any]:
        """
        Get detailed deposit statistics.

        Args:
            hours: Lookback period

        Returns:
            Dict with deposit details
        """
        return await self.financial_stats.get_deposit_details(hours)

    async def get_withdrawal_details(
        self, hours: int = 24
    ) -> dict[str, Any]:
        """
        Get detailed withdrawal statistics.

        Args:
            hours: Lookback period

        Returns:
            Dict with withdrawal details
        """
        return await self.financial_stats.get_withdrawal_details(hours)

    async def get_transaction_summary(
        self, hours: int = 24
    ) -> dict[str, Any]:
        """
        Get transaction summary by type.

        Args:
            hours: Lookback period

        Returns:
            Dict with transaction summary
        """
        return await self.financial_stats.get_transaction_summary(hours)

    # System health methods
    async def get_system_health(self) -> dict[str, Any]:
        """
        Get system health indicators.

        Returns:
            Dict with health metrics
        """
        return await self.system_health.get_system_health()

    async def get_server_metrics(self) -> dict[str, Any]:
        """
        Get server resource metrics (CPU, RAM, disk).

        Returns:
            Dict with server metrics
        """
        return await self.system_health.get_server_metrics()

    # User inquiries methods
    async def get_user_inquiries_stats(
        self, limit: int = 20
    ) -> dict[str, Any]:
        """
        Get user inquiries/questions statistics.

        Args:
            limit: Max recent inquiries to return

        Returns:
            Dict with inquiries stats
        """
        return await self.user_inquiries.get_user_inquiries_stats(limit)

    # Activity analytics methods
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
        return await self.activity.get_activity_analytics(hours)

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
        return await self.activity.get_user_journey(telegram_id)

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
        return await self.activity.format_activity_for_aria(hours)

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
        return await self.activity.get_ai_conversations_report(hours)

    # Dashboard methods
    async def get_full_dashboard(self) -> dict[str, Any]:
        """
        Get complete dashboard data for ARIA.

        Returns:
            Complete monitoring data
        """
        admin_stats = await self.get_admin_stats(hours=24)
        user_stats = await self.get_user_stats()
        financial_stats = await self.get_financial_stats(hours=24)
        recent_actions = await self.get_recent_admin_actions(limit=10)
        system_health = await self.get_system_health()
        server_metrics = await self.get_server_metrics()
        deposit_details = await self.get_deposit_details(hours=24)
        withdrawal_details = await self.get_withdrawal_details(hours=24)
        transaction_summary = await self.get_transaction_summary(hours=24)
        inquiries_stats = await self.get_user_inquiries_stats(limit=10)

        return {
            "admin": admin_stats,
            "users": user_stats,
            "financial": financial_stats,
            "recent_actions": recent_actions,
            "system": system_health,
            "server": server_metrics,
            "deposits": deposit_details,
            "withdrawals": withdrawal_details,
            "transactions": transaction_summary,
            "inquiries": inquiries_stats,
            "generated_at": datetime.now(UTC).isoformat(),
        }

    # Formatter methods
    def format_dashboard_for_ai(self, data: dict[str, Any]) -> str:
        """
        Format dashboard data as text for AI context.

        Args:
            data: Dashboard data dict

        Returns:
            Formatted text for AI prompt
        """
        return FormatterService.format_dashboard_for_ai(data)
