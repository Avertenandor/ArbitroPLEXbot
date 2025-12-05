"""
Withdrawal query service module.

Handles queries for withdrawal transactions including pending withdrawals,
user withdrawal history, and transaction lookups.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TransactionStatus, TransactionType
from app.models.transaction import Transaction


class WithdrawalQueryService:
    """Handles withdrawal query operations."""

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize withdrawal query service.

        Args:
            session: Database session
        """
        self.session = session

    async def get_pending_withdrawals(
        self,
    ) -> list[Transaction]:
        """
        Get pending withdrawals (for admin).

        Returns:
            List of pending withdrawal transactions
        """
        stmt = (
            select(Transaction)
            .where(
                Transaction.type == TransactionType.WITHDRAWAL.value,
                Transaction.status == TransactionStatus.PENDING.value,
            )
            .order_by(Transaction.created_at.asc())
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_withdrawals(
        self,
        user_id: int,
        page: int = 1,
        limit: int = 10,
    ) -> dict:
        """
        Get user withdrawal history.

        Args:
            user_id: User ID
            page: Page number (1-indexed)
            limit: Items per page

        Returns:
            Dict with withdrawals, total, page, pages
        """
        offset = (page - 1) * limit

        # Get total count using SQL COUNT (avoid loading all records)
        count_stmt = select(func.count(Transaction.id)).where(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.WITHDRAWAL.value,
        )
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Get paginated withdrawals
        stmt = (
            select(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.WITHDRAWAL.value,
            )
            .order_by(Transaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(stmt)
        withdrawals = list(result.scalars().all())

        pages = (total + limit - 1) // limit  # Ceiling division

        return {
            "withdrawals": withdrawals,
            "total": total,
            "page": page,
            "pages": pages,
        }

    async def get_withdrawal_by_id(
        self, transaction_id: int
    ) -> Transaction | None:
        """
        Get withdrawal by ID (admin only).

        Args:
            transaction_id: Transaction ID

        Returns:
            Transaction or None if not found
        """
        stmt = select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.type == TransactionType.WITHDRAWAL.value,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
