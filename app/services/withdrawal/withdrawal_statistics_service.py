"""
Withdrawal statistics service module.

Handles platform-wide withdrawal statistics, aggregations,
and detailed reporting for admin analytics.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TransactionStatus
from app.models.transaction import Transaction
from app.models.user import User


class WithdrawalStatisticsService:
    """Handles withdrawal statistics and reporting."""

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize withdrawal statistics service.

        Args:
            session: Database session
        """
        self.session = session

    async def get_platform_withdrawal_stats(self) -> dict:
        """
        Get platform-wide withdrawal statistics.

        Returns:
            Dictionary with withdrawal stats including:
            - total_confirmed: Total confirmed withdrawals count
            - total_confirmed_amount: Total amount of confirmed withdrawals
            - total_failed: Total failed withdrawals count
            - total_failed_amount: Total amount of failed withdrawals
            - by_user: List of users with their withdrawal amounts
        """
        # Get confirmed withdrawals stats
        confirmed_stmt = (
            select(
                func.count(Transaction.id).label("count"),
                func.coalesce(func.sum(Transaction.amount), 0).label("total"),
            )
            .where(
                Transaction.type == "withdrawal",
                Transaction.status == TransactionStatus.CONFIRMED.value,
            )
        )
        confirmed_result = await self.session.execute(confirmed_stmt)
        confirmed_row = confirmed_result.one()

        # Get failed withdrawals stats
        failed_stmt = (
            select(
                func.count(Transaction.id).label("count"),
                func.coalesce(func.sum(Transaction.amount), 0).label("total"),
            )
            .where(
                Transaction.type == "withdrawal",
                Transaction.status == TransactionStatus.FAILED.value,
            )
        )
        failed_result = await self.session.execute(failed_stmt)
        failed_row = failed_result.one()

        # Get per-user confirmed withdrawals
        by_user_stmt = (
            select(
                User.username,
                User.telegram_id,
                func.sum(Transaction.amount).label("total_withdrawn"),
            )
            .join(User, Transaction.user_id == User.id)
            .where(
                Transaction.type == "withdrawal",
                Transaction.status == TransactionStatus.CONFIRMED.value,
            )
            .group_by(User.id, User.username, User.telegram_id)
            .order_by(func.sum(Transaction.amount).desc())
        )
        by_user_result = await self.session.execute(by_user_stmt)
        by_user_rows = by_user_result.all()

        by_user_list = [
            {
                "username": row.username,
                "telegram_id": row.telegram_id,
                "total_withdrawn": row.total_withdrawn,
            }
            for row in by_user_rows
        ]

        return {
            "total_confirmed": confirmed_row.count,
            "total_confirmed_amount": confirmed_row.total,
            "total_failed": failed_row.count,
            "total_failed_amount": failed_row.total,
            "by_user": by_user_list,
        }

    async def get_detailed_withdrawals(
        self, page: int = 1, per_page: int = 5
    ) -> dict:
        """
        Get detailed withdrawal transactions with pagination.

        Args:
            page: Page number (1-based)
            per_page: Items per page

        Returns:
            Dictionary with withdrawals list and pagination info
        """
        # Count total confirmed withdrawals
        count_stmt = (
            select(func.count(Transaction.id))
            .where(
                Transaction.type == "withdrawal",
                Transaction.status == TransactionStatus.CONFIRMED.value,
            )
        )
        count_result = await self.session.execute(count_stmt)
        total_count = count_result.scalar() or 0

        # Calculate pagination
        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
        offset = (page - 1) * per_page

        # Get withdrawals with details
        withdrawals_stmt = (
            select(
                User.username,
                User.telegram_id,
                Transaction.amount,
                Transaction.tx_hash,
                Transaction.created_at,
            )
            .join(User, Transaction.user_id == User.id)
            .where(
                Transaction.type == "withdrawal",
                Transaction.status == TransactionStatus.CONFIRMED.value,
            )
            .order_by(Transaction.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        result = await self.session.execute(withdrawals_stmt)
        rows = result.all()

        withdrawals = [
            {
                "username": row.username,
                "telegram_id": row.telegram_id,
                "amount": row.amount,
                "tx_hash": row.tx_hash,
                "created_at": row.created_at,
            }
            for row in rows
        ]

        return {
            "withdrawals": withdrawals,
            "page": page,
            "per_page": per_page,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
        }
