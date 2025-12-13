"""
Deposit repository.

Data access layer for Deposit model.
"""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.deposit import Deposit
from app.models.enums import TransactionStatus
from app.repositories.base import BaseRepository


class DepositRepository(BaseRepository[Deposit]):
    """Deposit repository with specific queries."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize deposit repository."""
        super().__init__(Deposit, session)

    async def get_by_user(
        self, user_id: int, status: str | None = None
    ) -> list[Deposit]:
        """
        Get deposits by user.

        Args:
            user_id: User ID
            status: Optional status filter

        Returns:
            List of deposits
        """
        filters: dict[str, int | str] = {"user_id": user_id}
        if status:
            filters["status"] = status

        return await self.find_by(**filters)

    async def get_by_tx_hash(
        self, tx_hash: str
    ) -> Deposit | None:
        """
        Get deposit by transaction hash.

        Args:
            tx_hash: Transaction hash

        Returns:
            Deposit or None
        """
        return await self.get_by(tx_hash=tx_hash)

    async def get_active_deposits(
        self, user_id: int
    ) -> list[Deposit]:
        """
        Get active deposits (ROI not completed).

        Args:
            user_id: User ID

        Returns:
            List of active deposits
        """
        stmt = (
            select(Deposit)
            .where(Deposit.user_id == user_id)
            .where(Deposit.is_roi_completed == False)  # noqa: E712
            .where(
                Deposit.status == TransactionStatus.CONFIRMED.value
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_level(
        self, user_id: int, level: int
    ) -> list[Deposit]:
        """
        Get deposits by user and level.

        Args:
            user_id: User ID
            level: Deposit level (1-5)

        Returns:
            List of deposits
        """
        return await self.find_by(user_id=user_id, level=level)

    async def get_pending_deposits(self) -> list[Deposit]:
        """
        Get all pending deposits.

        Returns:
            List of pending deposits
        """
        return await self.find_by(
            status=TransactionStatus.PENDING.value
        )

    async def get_total_deposited(
        self, user_id: int
    ) -> Decimal:
        """
        Get total deposited amount by user.

        Args:
            user_id: User ID

        Returns:
            Total deposited amount
        """
        stmt = (
            select(func.sum(Deposit.amount))
            .where(Deposit.user_id == user_id)
            .where(Deposit.status == TransactionStatus.CONFIRMED.value)
        )
        result = await self.session.execute(stmt)
        total = result.scalar()
        return total or Decimal("0")

    async def get_with_user(self, deposit_id: int) -> Deposit | None:
        """
        Get deposit by ID with user eager loaded.

        Args:
            deposit_id: Deposit ID

        Returns:
            Deposit with user or None
        """
        stmt = (
            select(Deposit)
            .options(selectinload(Deposit.user))
            .where(Deposit.id == deposit_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_many_with_user(
        self, deposit_ids: list[int]
    ) -> list[Deposit]:
        """
        Get multiple deposits with users eager loaded.

        Args:
            deposit_ids: List of deposit IDs

        Returns:
            List of deposits with users loaded
        """
        stmt = (
            select(Deposit)
            .options(selectinload(Deposit.user))
            .where(Deposit.id.in_(deposit_ids))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_deposits_with_user(
        self, user_id: int
    ) -> list[Deposit]:
        """
        Get active deposits with user eager loaded.

        Args:
            user_id: User ID

        Returns:
            List of active deposits with user loaded
        """
        stmt = (
            select(Deposit)
            .options(selectinload(Deposit.user))
            .where(Deposit.user_id == user_id)
            .where(Deposit.is_roi_completed == False)  # noqa: E712
            .where(Deposit.status == TransactionStatus.CONFIRMED.value)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
