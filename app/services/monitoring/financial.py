"""
Financial Monitoring Module.

Provides financial metrics and statistics for the ARIA AI Assistant.
Includes optimized queries to minimize database round-trips.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deposit import Deposit
from app.models.transaction import Transaction
from app.models.user import User


# Status constants
STATUS_ACTIVE = "active"
STATUS_PENDING = "pending"
STATUS_WITHDRAWAL = "withdrawal"


class FinancialMonitor:
    """
    Financial monitoring service for tracking deposits, withdrawals, and transactions.

    Provides optimized queries for financial statistics with minimal database overhead.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize financial monitor.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session

    async def get_stats(self, hours: int = 24) -> dict[str, Any]:
        """
        Get comprehensive financial statistics with optimized queries.

        This method combines multiple queries into 2 efficient database calls:
        - Query 1: All deposit-related metrics
        - Query 2: All transaction-related metrics (withdrawals, pending)

        Args:
            hours: Lookback period in hours for recent activity (default: 24)

        Returns:
            Dict containing:
                - hours_period: The lookback period used
                - total_active_deposits: Total amount of all active deposits
                - total_deposits_count: Count of all active deposits
                - recent_deposits: Sum of deposits created in the period
                - recent_deposits_count: Count of deposits created in the period
                - recent_withdrawals: Sum of withdrawals in the period
                - recent_withdrawals_count: Count of withdrawals in the period
                - pending_withdrawals_count: Count of pending withdrawals
                - pending_withdrawals_amount: Total amount of pending withdrawals

        Example:
            >>> monitor = FinancialMonitor(session)
            >>> stats = await monitor.get_stats(hours=24)
            >>> print(f"Active deposits: ${stats['total_active_deposits']}")
        """
        try:
            since = datetime.now(UTC) - timedelta(hours=hours)

            # Query 1: Optimized deposits query - combines 4 queries into 1
            # Gets: total active deposits, active count, recent deposits, recent count
            deposits_query = select(
                func.sum(
                    case((Deposit.status == STATUS_ACTIVE, Deposit.amount), else_=0)
                ).label('total_active'),
                func.count(
                    case((Deposit.status == STATUS_ACTIVE, Deposit.id))
                ).label('total_count'),
                func.sum(
                    case((Deposit.created_at >= since, Deposit.amount), else_=0)
                ).label('recent_sum'),
                func.count(
                    case((Deposit.created_at >= since, Deposit.id))
                ).label('recent_count')
            )

            deposits_result = await self.session.execute(deposits_query)
            deposits_row = deposits_result.fetchone()

            # Extract deposit metrics
            total_deposits = deposits_row[0] or Decimal("0")
            deposits_count = deposits_row[1] or 0
            recent_deposits = deposits_row[2] or Decimal("0")
            recent_deposits_count = deposits_row[3] or 0

            # Query 2: Optimized transactions query - combines 3 queries into 1
            # Gets: withdrawals sum, withdrawals count, pending count, pending sum
            transactions_query = select(
                func.sum(
                    case((Transaction.type == STATUS_WITHDRAWAL, Transaction.amount), else_=0)
                ).label('withdrawals_sum'),
                func.count(
                    case((Transaction.type == STATUS_WITHDRAWAL, Transaction.id))
                ).label('withdrawals_count'),
                func.count(
                    case(
                        ((Transaction.type == STATUS_WITHDRAWAL) & (Transaction.status == STATUS_PENDING),
                         Transaction.id)
                    )
                ).label('pending_count'),
                func.sum(
                    case(
                        ((Transaction.type == STATUS_WITHDRAWAL) & (Transaction.status == STATUS_PENDING),
                         Transaction.amount),
                        else_=0
                    )
                ).label('pending_sum')
            ).where(Transaction.created_at >= since)

            transactions_result = await self.session.execute(transactions_query)
            transactions_row = transactions_result.fetchone()

            # Extract transaction metrics
            withdrawals = transactions_row[0] or Decimal("0")
            withdrawals_count = transactions_row[1] or 0
            pending_count = transactions_row[2] or 0
            pending_amount = transactions_row[3] or Decimal("0")

            logger.debug(
                f"FinancialMonitor: Retrieved stats for {hours}h period - "
                f"Active deposits: ${total_deposits}, Recent: ${recent_deposits}, "
                f"Withdrawals: ${withdrawals}, Pending: {pending_count}"
            )

            return {
                "hours_period": hours,
                "total_active_deposits": float(total_deposits),
                "total_deposits_count": deposits_count,
                "recent_deposits": float(recent_deposits),
                "recent_deposits_count": recent_deposits_count,
                "recent_withdrawals": float(withdrawals),
                "recent_withdrawals_count": withdrawals_count,
                "pending_withdrawals_count": pending_count,
                "pending_withdrawals_amount": float(pending_amount),
            }

        except Exception as e:
            logger.error(f"Error getting financial stats: {e}")
            return {"error": str(e)}

    async def get_deposit_details(self, hours: int = 24) -> dict[str, Any]:
        """
        Get detailed deposit statistics and breakdown.

        Args:
            hours: Lookback period in hours for recent deposits (default: 24)

        Returns:
            Dict containing:
                - by_status: Dict of {status: {count, amount}} for all statuses
                - recent: List of recent deposits with details
                - today_count: Number of deposits created today
                - today_amount: Total amount deposited today

        Example:
            >>> details = await monitor.get_deposit_details(hours=48)
            >>> print(f"Deposits by status: {details['by_status']}")
        """
        try:
            since = datetime.now(UTC) - timedelta(hours=hours)

            # Deposits grouped by status
            status_result = await self.session.execute(
                select(
                    Deposit.status,
                    func.count(Deposit.id),
                    func.sum(Deposit.amount)
                ).group_by(Deposit.status)
            )
            by_status = {
                row[0]: {"count": row[1], "amount": float(row[2] or 0)}
                for row in status_result.fetchall()
            }

            # Recent deposits list with user information
            recent_result = await self.session.execute(
                select(
                    Deposit.amount,
                    Deposit.status,
                    Deposit.created_at,
                    User.username,
                )
                .join(User, Deposit.user_id == User.id)
                .where(Deposit.created_at >= since)
                .order_by(Deposit.created_at.desc())
                .limit(10)
            )
            recent_deposits = [
                {
                    "amount": float(row[0]),
                    "status": row[1],
                    "time": row[2].strftime("%d.%m %H:%M") if row[2] else "",
                    "user": row[3] or "Unknown",
                }
                for row in recent_result.fetchall()
            ]

            # Today's deposits (from midnight UTC)
            today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
            today_result = await self.session.execute(
                select(
                    func.count(Deposit.id),
                    func.sum(Deposit.amount)
                ).where(Deposit.created_at >= today_start)
            )
            today_row = today_result.fetchone()

            logger.debug(
                f"FinancialMonitor: Retrieved deposit details - "
                f"Today: {today_row[0] or 0} deposits, ${float(today_row[1] or 0)}"
            )

            return {
                "by_status": by_status,
                "recent": recent_deposits,
                "today_count": today_row[0] or 0,
                "today_amount": float(today_row[1] or 0),
            }

        except Exception as e:
            logger.error(f"Error getting deposit details: {e}")
            return {"error": str(e)}

    async def get_withdrawal_details(self, hours: int = 24) -> dict[str, Any]:
        """
        Get detailed withdrawal statistics and pending list.

        Args:
            hours: Lookback period in hours (default: 24)

        Returns:
            Dict containing:
                - by_status: Dict of {status: {count, amount}} for all withdrawal statuses
                - pending_list: List of pending withdrawals with user details
                - pending_count: Total number of pending withdrawals

        Example:
            >>> details = await monitor.get_withdrawal_details()
            >>> for withdrawal in details['pending_list']:
            ...     print(f"Pending: ${withdrawal['amount']} for {withdrawal['user']}")
        """
        try:
            # Withdrawals grouped by status
            status_result = await self.session.execute(
                select(
                    Transaction.status,
                    func.count(Transaction.id),
                    func.sum(Transaction.amount)
                )
                .where(Transaction.type == STATUS_WITHDRAWAL)
                .group_by(Transaction.status)
            )
            by_status = {
                row[0]: {"count": row[1], "amount": float(row[2] or 0)}
                for row in status_result.fetchall()
            }

            # Pending withdrawals with detailed information
            pending_result = await self.session.execute(
                select(
                    Transaction.amount,
                    Transaction.created_at,
                    User.username,
                )
                .join(User, Transaction.user_id == User.id)
                .where(Transaction.type == STATUS_WITHDRAWAL)
                .where(Transaction.status == STATUS_PENDING)
                .order_by(Transaction.created_at.asc())  # Oldest first
                .limit(20)
            )
            pending_list = [
                {
                    "amount": float(row[0]),
                    "waiting_since": row[1].strftime("%d.%m %H:%M") if row[1] else "",
                    "user": row[2] or "Unknown",
                }
                for row in pending_result.fetchall()
            ]

            logger.debug(
                f"FinancialMonitor: Retrieved withdrawal details - "
                f"Pending: {len(pending_list)} withdrawals"
            )

            return {
                "by_status": by_status,
                "pending_list": pending_list,
                "pending_count": len(pending_list),
            }

        except Exception as e:
            logger.error(f"Error getting withdrawal details: {e}")
            return {"error": str(e)}

    async def get_transaction_summary(self, hours: int = 24) -> dict[str, Any]:
        """
        Get transaction summary grouped by type.

        Args:
            hours: Lookback period in hours (default: 24)

        Returns:
            Dict of {transaction_type: {count, total}} for all transaction types
            in the specified time period

        Example:
            >>> summary = await monitor.get_transaction_summary(hours=24)
            >>> for tx_type, data in summary.items():
            ...     print(f"{tx_type}: {data['count']} transactions, ${data['total']}")
        """
        try:
            since = datetime.now(UTC) - timedelta(hours=hours)

            # Group transactions by type with counts and totals
            result = await self.session.execute(
                select(
                    Transaction.type,
                    func.count(Transaction.id),
                    func.sum(Transaction.amount)
                )
                .where(Transaction.created_at >= since)
                .group_by(Transaction.type)
            )

            summary = {}
            for row in result.fetchall():
                summary[row[0]] = {
                    "count": row[1],
                    "total": float(row[2] or 0)
                }

            logger.debug(
                f"FinancialMonitor: Retrieved transaction summary for {hours}h - "
                f"{len(summary)} transaction types"
            )

            return summary

        except Exception as e:
            logger.error(f"Error getting transaction summary: {e}")
            return {"error": str(e)}
