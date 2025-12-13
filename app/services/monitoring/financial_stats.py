"""Financial statistics module for MonitoringService."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deposit import Deposit
from app.models.enums import DepositStatus, TransactionStatus
from app.models.transaction import Transaction
from app.models.user import User


class FinancialStatsService:
    """Service for collecting financial statistics."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize financial stats service."""
        self.session = session

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
        try:
            since = datetime.now(UTC) - timedelta(hours=hours)

            # Total deposits (all time)
            total_deposits_result = await self.session.execute(
                select(func.sum(Deposit.amount))
                .where(Deposit.status == DepositStatus.ACTIVE.value)
            )
            total_deposits = total_deposits_result.scalar() or Decimal("0")

            # Deposits count
            deposits_count_result = await self.session.execute(
                select(func.count(Deposit.id))
                .where(Deposit.status == DepositStatus.ACTIVE.value)
            )
            deposits_count = deposits_count_result.scalar() or 0

            # Recent deposits (period)
            recent_deposits_result = await self.session.execute(
                select(func.sum(Deposit.amount))
                .where(Deposit.created_at >= since)
            )
            recent_deposits = recent_deposits_result.scalar() or Decimal("0")

            # Recent deposits count
            recent_count_result = await self.session.execute(
                select(func.count(Deposit.id))
                .where(Deposit.created_at >= since)
            )
            recent_deposits_count = recent_count_result.scalar() or 0

            # Withdrawals (period)
            withdrawals_result = await self.session.execute(
                select(func.sum(Transaction.amount))
                .where(Transaction.type == "withdrawal")
                .where(Transaction.created_at >= since)
            )
            withdrawals = withdrawals_result.scalar() or Decimal("0")

            withdrawals_count_result = await self.session.execute(
                select(func.count(Transaction.id))
                .where(Transaction.type == "withdrawal")
                .where(Transaction.created_at >= since)
            )
            withdrawals_count = withdrawals_count_result.scalar() or 0

            # Pending withdrawals
            pending_result = await self.session.execute(
                select(
                    func.count(Transaction.id),
                    func.sum(Transaction.amount),
                )
                .where(Transaction.type == "withdrawal")
                .where(Transaction.status == TransactionStatus.PENDING.value)
            )
            pending_row = pending_result.fetchone()
            pending_count = pending_row[0] or 0
            pending_amount = pending_row[1] or Decimal("0")

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
        try:
            since = datetime.now(UTC) - timedelta(hours=hours)

            # Deposits by status
            status_result = await self.session.execute(
                select(
                    Deposit.status,
                    func.count(Deposit.id),
                    func.sum(Deposit.amount),
                ).group_by(Deposit.status)
            )
            by_status = {
                row[0]: {"count": row[1], "amount": float(row[2] or 0)}
                for row in status_result.fetchall()
            }

            # Recent deposits list
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
                    "time": (
                        row[2].strftime("%d.%m %H:%M") if row[2] else ""
                    ),
                    "user": row[3] or "Unknown",
                }
                for row in recent_result.fetchall()
            ]

            # Today's deposits
            today_start = datetime.now(UTC).replace(
                hour=0, minute=0, second=0
            )
            today_result = await self.session.execute(
                select(func.count(Deposit.id), func.sum(Deposit.amount))
                .where(Deposit.created_at >= today_start)
            )
            today_row = today_result.fetchone()

            return {
                "by_status": by_status,
                "recent": recent_deposits,
                "today_count": today_row[0] or 0,
                "today_amount": float(today_row[1] or 0),
            }
        except Exception as e:
            logger.error(f"Error getting deposit details: {e}")
            return {"error": str(e)}

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
        try:
            # Withdrawals by status
            status_result = await self.session.execute(
                select(
                    Transaction.status,
                    func.count(Transaction.id),
                    func.sum(Transaction.amount),
                )
                .where(Transaction.type == "withdrawal")
                .group_by(Transaction.status)
            )
            by_status = {
                row[0]: {"count": row[1], "amount": float(row[2] or 0)}
                for row in status_result.fetchall()
            }

            # Pending withdrawals (detailed)
            pending_result = await self.session.execute(
                select(
                    Transaction.amount,
                    Transaction.created_at,
                    User.username,
                )
                .join(User, Transaction.user_id == User.id)
                .where(Transaction.type == "withdrawal")
                .where(Transaction.status == TransactionStatus.PENDING.value)
                .order_by(Transaction.created_at.asc())
                .limit(20)
            )
            pending_list = [
                {
                    "amount": float(row[0]),
                    "waiting_since": (
                        row[1].strftime("%d.%m %H:%M") if row[1] else ""
                    ),
                    "user": row[2] or "Unknown",
                }
                for row in pending_result.fetchall()
            ]

            return {
                "by_status": by_status,
                "pending_list": pending_list,
                "pending_count": len(pending_list),
            }
        except Exception as e:
            logger.error(f"Error getting withdrawal details: {e}")
            return {"error": str(e)}

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
        try:
            since = datetime.now(UTC) - timedelta(hours=hours)

            result = await self.session.execute(
                select(
                    Transaction.type,
                    func.count(Transaction.id),
                    func.sum(Transaction.amount),
                )
                .where(Transaction.created_at >= since)
                .group_by(Transaction.type)
            )

            summary = {}
            for row in result.fetchall():
                summary[row[0]] = {
                    "count": row[1],
                    "total": float(row[2] or 0),
                }

            return summary
        except Exception as e:
            logger.error(f"Error getting transaction summary: {e}")
            return {"error": str(e)}
