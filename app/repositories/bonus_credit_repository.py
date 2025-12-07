"""
BonusCredit repository.

Data access layer for BonusCredit model.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.bonus_credit import BonusCredit
from app.repositories.base import BaseRepository


class BonusCreditRepository(BaseRepository[BonusCredit]):
    """Repository for bonus credit operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository."""
        super().__init__(BonusCredit, session)

    async def get_active_by_user(self, user_id: int) -> list[BonusCredit]:
        """
        Get all active bonus credits for a user.

        Args:
            user_id: User ID

        Returns:
            List of active bonus credits
        """
        query = (
            select(BonusCredit)
            .where(
                and_(
                    BonusCredit.user_id == user_id,
                    BonusCredit.is_active == True,  # noqa: E712
                    BonusCredit.is_roi_completed == False,  # noqa: E712
                )
            )
            .order_by(BonusCredit.created_at.asc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_all_by_user(self, user_id: int) -> list[BonusCredit]:
        """
        Get all bonus credits for a user (including completed/cancelled).

        Args:
            user_id: User ID

        Returns:
            List of all bonus credits
        """
        query = (
            select(BonusCredit)
            .where(BonusCredit.user_id == user_id)
            .order_by(BonusCredit.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_total_active_bonus(self, user_id: int) -> Decimal:
        """
        Get total active bonus amount for a user.

        Args:
            user_id: User ID

        Returns:
            Total active bonus amount
        """
        query = select(func.coalesce(func.sum(BonusCredit.amount), 0)).where(
            and_(
                BonusCredit.user_id == user_id,
                BonusCredit.is_active == True,  # noqa: E712
                BonusCredit.is_roi_completed == False,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return result.scalar() or Decimal("0")

    async def get_due_for_accrual(self, now: datetime) -> list[BonusCredit]:
        """
        Get bonus credits due for ROI accrual.

        Args:
            now: Current datetime

        Returns:
            List of bonus credits ready for accrual
        """
        query = (
            select(BonusCredit)
            .where(
                and_(
                    BonusCredit.is_active == True,  # noqa: E712
                    BonusCredit.is_roi_completed == False,  # noqa: E712
                    BonusCredit.next_accrual_at <= now,
                )
            )
            .with_for_update()  # Lock for concurrent processing
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_with_user(self, bonus_id: int) -> BonusCredit | None:
        """
        Get bonus credit with user eager loaded.

        Args:
            bonus_id: Bonus credit ID

        Returns:
            BonusCredit with user or None
        """
        query = (
            select(BonusCredit)
            .options(selectinload(BonusCredit.user))
            .where(BonusCredit.id == bonus_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_roi(
        self,
        bonus_id: int,
        roi_paid_amount: Decimal,
        next_accrual_at: datetime | None = None,
        is_completed: bool = False,
        completed_at: datetime | None = None,
    ) -> None:
        """
        Update ROI tracking fields.

        Args:
            bonus_id: Bonus credit ID
            roi_paid_amount: New ROI paid amount
            next_accrual_at: Next accrual time
            is_completed: Whether ROI is completed
            completed_at: Completion timestamp
        """
        values = {
            "roi_paid_amount": roi_paid_amount,
        }
        if next_accrual_at is not None:
            values["next_accrual_at"] = next_accrual_at
        if is_completed:
            values["is_roi_completed"] = True
            values["is_active"] = False
            if completed_at:
                values["completed_at"] = completed_at

        stmt = (
            update(BonusCredit)
            .where(BonusCredit.id == bonus_id)
            .values(**values)
        )
        await self.session.execute(stmt)

    async def cancel(
        self,
        bonus_id: int,
        cancelled_by: int,
        cancel_reason: str,
        cancelled_at: datetime,
    ) -> bool:
        """
        Cancel a bonus credit.

        Args:
            bonus_id: Bonus credit ID
            cancelled_by: Admin ID who cancelled
            cancel_reason: Reason for cancellation
            cancelled_at: Cancellation timestamp

        Returns:
            True if cancelled successfully
        """
        stmt = (
            update(BonusCredit)
            .where(
                and_(
                    BonusCredit.id == bonus_id,
                    BonusCredit.is_active == True,  # noqa: E712
                )
            )
            .values(
                is_active=False,
                cancelled_at=cancelled_at,
                cancelled_by=cancelled_by,
                cancel_reason=cancel_reason,
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
