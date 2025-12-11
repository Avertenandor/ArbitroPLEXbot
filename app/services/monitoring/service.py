"""
Monitoring Service Facade.

Main orchestrator that maintains backward compatibility with the original API.
Delegates all operations to specialized monitor classes.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from .formatters.activity_formatter import ActivityFormatter
from .formatters.dashboard_formatter import DashboardFormatter
from .monitors.activity_monitor import ActivityMonitor
from .monitors.admin_monitor import AdminMonitor
from .monitors.financial_monitor import FinancialMonitor
from .monitors.system_monitor import SystemMonitor
from .monitors.user_monitor import UserMonitor


class MonitoringService:
    """
    Monitoring Service Facade.

    Orchestrates all monitoring operations by delegating to specialized monitors.
    Maintains backward compatibility with the original MonitoringService API.

    This facade pattern allows for:
    - Clean separation of concerns
    - Easier testing of individual components
    - Better code organization and maintainability
    - Parallel execution of independent monitoring tasks
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the monitoring service with all specialized monitors.

        Args:
            session: Database session for executing queries
        """
        self.session = session
        self._admin = AdminMonitor(session)
        self._users = UserMonitor(session)
        self._financial = FinancialMonitor(session)
        self._system = SystemMonitor(session)
        self._activity = ActivityMonitor(session)

    # ==================== Admin Monitoring ====================

    async def get_admin_stats(self, hours: int = 24) -> dict[str, Any]:
        """
        Get admin activity statistics.

        Args:
            hours: Lookback period in hours

        Returns:
            Dict with admin statistics including:
            - total_admins: Total number of admins
            - active_admins_last_hours: Active admins in the period
            - total_actions: Total admin actions in the period
            - top_action_types: Most common action types
            - admins_list: List of all admins with roles
        """
        return await self._admin.get_stats(hours)

    async def get_recent_admin_actions(self, limit: int = 10, hours: int = 24) -> list[dict[str, Any]]:
        """
        Get recent admin actions log.

        Args:
            limit: Max number of actions to return
            hours: Lookback period in hours

        Returns:
            List of recent admin actions with type, description, time, and admin
        """
        return await self._admin.get_recent_actions(limit, hours)

    # ==================== User Monitoring ====================

    async def get_user_stats(self) -> dict[str, Any]:
        """
        Get user statistics.

        Returns:
            Dict with user statistics including:
            - total_users: Total number of users
            - active_24h: Active users in last 24 hours
            - active_7d: Active users in last 7 days
            - new_today: New users registered today
            - new_last_hour: New users in last hour
            - verified_users: Number of verified users
            - verification_rate: Percentage of verified users
        """
        return await self._users.get_stats()

    async def get_user_full_history(self, identifier: str | int) -> dict[str, Any]:
        """
        Get full history for a user by username, telegram_id, or user_id.

        Args:
            identifier: Username (with or without @), telegram_id, or user_id

        Returns:
            Dict with complete user history including:
            - found: Whether user was found
            - user: Basic user information
            - deposits: List of all deposits
            - transactions: List of recent transactions
            - inquiries: List of user inquiries (if available)
            - admin_actions: Admin actions related to this user
        """
        return await self._users.get_full_history(identifier)

    async def search_users(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Search users by username, telegram_id, or wallet.

        Args:
            query: Search query (username, telegram_id, etc.)
            limit: Maximum number of results

        Returns:
            List of matching users with basic information
        """
        return await self._users.search(query, limit)

    # ==================== Financial Monitoring ====================

    async def get_financial_stats(self, hours: int = 24) -> dict[str, Any]:
        """
        Get financial statistics.

        Args:
            hours: Lookback period in hours

        Returns:
            Dict with financial stats including:
            - total_active_deposits: Total amount of active deposits
            - recent_deposits: Deposits in the period
            - recent_withdrawals: Withdrawals in the period
            - pending_withdrawals_count: Number of pending withdrawals
            - pending_withdrawals_amount: Total amount pending withdrawal
        """
        return await self._financial.get_stats(hours)

    async def get_deposit_details(self, hours: int = 24) -> dict[str, Any]:
        """
        Get detailed deposit statistics.

        Args:
            hours: Lookback period in hours

        Returns:
            Dict with deposit details including:
            - by_status: Deposits grouped by status
            - recent: List of recent deposits
            - today_count: Number of deposits today
            - today_amount: Total amount deposited today
        """
        return await self._financial.get_deposit_details(hours)

    async def get_withdrawal_details(self, hours: int = 24) -> dict[str, Any]:
        """
        Get detailed withdrawal statistics.

        Args:
            hours: Lookback period in hours

        Returns:
            Dict with withdrawal details including:
            - by_status: Withdrawals grouped by status
            - pending_list: List of pending withdrawals
            - pending_count: Number of pending withdrawals
        """
        return await self._financial.get_withdrawal_details(hours)

    async def get_transaction_summary(self, hours: int = 24) -> dict[str, Any]:
        """
        Get transaction summary by type.

        Args:
            hours: Lookback period in hours

        Returns:
            Dict mapping transaction types to counts and totals
        """
        return await self._financial.get_transaction_summary(hours)

    # ==================== System Monitoring ====================

    async def get_system_health(self) -> dict[str, Any]:
        """
        Get system health indicators.

        Returns:
            Dict with health metrics including:
            - database: Database status
            - timestamp: Current timestamp
            - status: Overall system status
        """
        return await self._system.get_health()

    async def get_server_metrics(self) -> dict[str, Any]:
        """
        Get server resource metrics (CPU, RAM, disk).

        Returns:
            Dict with server metrics including:
            - cpu_percent: CPU usage percentage
            - cpu_cores: Number of CPU cores
            - memory_total_gb: Total memory in GB
            - memory_used_gb: Used memory in GB
            - memory_percent: Memory usage percentage
            - disk_total_gb: Total disk space in GB
            - disk_used_gb: Used disk space in GB
            - disk_percent: Disk usage percentage
            - bot_memory_mb: Bot process memory usage in MB
        """
        return await self._system.get_server_metrics()

    # ==================== Activity Monitoring ====================

    async def get_user_inquiries_stats(self, limit: int = 20) -> dict[str, Any]:
        """
        Get user inquiries/questions statistics.

        Args:
            limit: Maximum number of recent inquiries to return

        Returns:
            Dict with inquiries stats including:
            - available: Whether inquiries module is available
            - total: Total number of inquiries
            - by_status: Inquiries grouped by status
            - new_count: Number of new inquiries
            - in_progress_count: Number of inquiries in progress
            - closed_count: Number of closed inquiries
            - recent: List of recent inquiries
        """
        return await self._activity.get_inquiries_stats(limit)

    async def get_activity_analytics(self, hours: int = 24) -> dict[str, Any]:
        """
        Get comprehensive user activity analytics.

        Args:
            hours: Lookback period in hours

        Returns:
            Dict with activity statistics, funnel, and conversions
        """
        return await self._activity.get_analytics(hours)

    async def get_user_journey(self, telegram_id: int) -> list[dict[str, Any]]:
        """
        Get complete journey of a specific user.

        Args:
            telegram_id: User's Telegram ID

        Returns:
            List of user activities in chronological order
        """
        return await self._activity.get_user_journey(telegram_id)

    # ==================== Dashboard ====================

    async def get_full_dashboard(self) -> dict[str, Any]:
        """
        Get complete dashboard data for ARIA.

        Executes all monitoring queries in parallel using asyncio.gather
        for optimal performance.

        Returns:
            Complete monitoring data including:
            - admin: Admin statistics
            - users: User statistics
            - financial: Financial statistics
            - recent_actions: Recent admin actions
            - system: System health
            - server: Server metrics
            - deposits: Deposit details
            - withdrawals: Withdrawal details
            - transactions: Transaction summary
            - inquiries: User inquiries stats
            - generated_at: Timestamp of generation
        """
        # Execute all queries in parallel for better performance
        results = await asyncio.gather(
            self.get_admin_stats(hours=24),
            self.get_user_stats(),
            self.get_financial_stats(hours=24),
            self.get_recent_admin_actions(limit=10),
            self.get_system_health(),
            self.get_server_metrics(),
            self.get_deposit_details(hours=24),
            self.get_withdrawal_details(hours=24),
            self.get_transaction_summary(hours=24),
            self.get_user_inquiries_stats(limit=10),
        )

        return {
            "admin": results[0],
            "users": results[1],
            "financial": results[2],
            "recent_actions": results[3],
            "system": results[4],
            "server": results[5],
            "deposits": results[6],
            "withdrawals": results[7],
            "transactions": results[8],
            "inquiries": results[9],
            "generated_at": datetime.now(UTC).isoformat(),
        }

    # ==================== Formatting ====================

    def format_dashboard_for_ai(self, data: dict[str, Any]) -> str:
        """
        Format dashboard data as text for AI context.

        Args:
            data: Dashboard data dict from get_full_dashboard()

        Returns:
            Formatted text for AI prompt with all platform metrics
        """
        return DashboardFormatter.format(data)

    async def format_activity_for_aria(self, hours: int = 24) -> str:
        """
        Format activity statistics for ARIA assistant.

        Uses separate session to avoid transaction conflicts.

        Args:
            hours: Lookback period in hours

        Returns:
            Formatted text report of user activity
        """
        return await ActivityFormatter.format_for_aria(hours)

    async def get_ai_conversations_report(self, hours: int = 24) -> str:
        """
        Get AI conversations report for ARIA.

        Uses separate session to avoid transaction conflicts.

        Args:
            hours: Lookback period in hours

        Returns:
            Formatted text with recent AI conversations
        """
        return await ActivityFormatter.get_ai_conversations_report(hours)
