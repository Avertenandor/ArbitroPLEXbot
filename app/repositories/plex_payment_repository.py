"""
PLEX Payment Repository.

Database operations for PlexPaymentRequirement model.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Sequence

from loguru import logger
from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.plex_payment import PlexPaymentRequirement, PlexPaymentStatus


class PlexPaymentRepository:
    """Repository for PLEX payment requirements."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        self._session = session

    async def create(
        self,
        user_id: int,
        deposit_id: int,
        daily_plex_required: Decimal,
        deposit_created_at: datetime,
    ) -> PlexPaymentRequirement:
        """
        Create a new PLEX payment requirement.
        
        Args:
            user_id: User ID
            deposit_id: Deposit ID
            daily_plex_required: Daily PLEX amount required
            deposit_created_at: When the deposit was created
            
        Returns:
            Created PlexPaymentRequirement
        """
        next_payment_due, warning_due, block_due = (
            PlexPaymentRequirement.calculate_deadlines(deposit_created_at)
        )
        
        payment = PlexPaymentRequirement(
            user_id=user_id,
            deposit_id=deposit_id,
            daily_plex_required=daily_plex_required,
            next_payment_due=next_payment_due,
            warning_due=warning_due,
            block_due=block_due,
            status=PlexPaymentStatus.ACTIVE,
        )
        
        self._session.add(payment)
        await self._session.flush()
        await self._session.refresh(payment)
        
        logger.info(
            f"Created PLEX payment requirement: "
            f"user_id={user_id}, deposit_id={deposit_id}, "
            f"daily_plex={daily_plex_required}"
        )
        
        return payment

    async def get_by_id(self, payment_id: int) -> PlexPaymentRequirement | None:
        """Get payment requirement by ID."""
        result = await self._session.execute(
            select(PlexPaymentRequirement)
            .where(PlexPaymentRequirement.id == payment_id)
            .options(selectinload(PlexPaymentRequirement.user))
            .options(selectinload(PlexPaymentRequirement.deposit))
        )
        return result.scalar_one_or_none()

    async def get_by_deposit_id(
        self, deposit_id: int
    ) -> PlexPaymentRequirement | None:
        """Get payment requirement for a specific deposit."""
        result = await self._session.execute(
            select(PlexPaymentRequirement)
            .where(PlexPaymentRequirement.deposit_id == deposit_id)
            .options(selectinload(PlexPaymentRequirement.user))
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(
        self, user_id: int
    ) -> Sequence[PlexPaymentRequirement]:
        """Get all payment requirements for a user."""
        result = await self._session.execute(
            select(PlexPaymentRequirement)
            .where(PlexPaymentRequirement.user_id == user_id)
            .options(selectinload(PlexPaymentRequirement.deposit))
            .order_by(PlexPaymentRequirement.created_at.desc())
        )
        return result.scalars().all()

    async def get_active_by_user_id(
        self, user_id: int
    ) -> Sequence[PlexPaymentRequirement]:
        """Get active payment requirements for a user."""
        result = await self._session.execute(
            select(PlexPaymentRequirement)
            .where(
                and_(
                    PlexPaymentRequirement.user_id == user_id,
                    PlexPaymentRequirement.status.in_([
                        PlexPaymentStatus.ACTIVE,
                        PlexPaymentStatus.WARNING_SENT,
                        PlexPaymentStatus.PAID,
                    ])
                )
            )
            .options(selectinload(PlexPaymentRequirement.deposit))
            .order_by(PlexPaymentRequirement.next_payment_due.asc())
        )
        return result.scalars().all()

    async def get_overdue_payments(
        self, limit: int = 100
    ) -> Sequence[PlexPaymentRequirement]:
        """
        Get payment requirements that are overdue (past next_payment_due).
        
        Returns payments that are active and past their due date.
        """
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(PlexPaymentRequirement)
            .where(
                and_(
                    PlexPaymentRequirement.next_payment_due < now,
                    PlexPaymentRequirement.status.in_([
                        PlexPaymentStatus.ACTIVE,
                        PlexPaymentStatus.PAID,  # Previous day paid, need to check new day
                    ])
                )
            )
            .options(selectinload(PlexPaymentRequirement.user))
            .options(selectinload(PlexPaymentRequirement.deposit))
            .order_by(PlexPaymentRequirement.next_payment_due.asc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_warning_due_payments(
        self, limit: int = 100
    ) -> Sequence[PlexPaymentRequirement]:
        """
        Get payment requirements that need warning sent.
        
        Returns active payments past warning_due but not yet warned.
        """
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(PlexPaymentRequirement)
            .where(
                and_(
                    PlexPaymentRequirement.warning_due < now,
                    PlexPaymentRequirement.status == PlexPaymentStatus.ACTIVE,
                    PlexPaymentRequirement.warning_sent_at.is_(None),
                )
            )
            .options(selectinload(PlexPaymentRequirement.user))
            .options(selectinload(PlexPaymentRequirement.deposit))
            .order_by(PlexPaymentRequirement.warning_due.asc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_block_due_payments(
        self, limit: int = 100
    ) -> Sequence[PlexPaymentRequirement]:
        """
        Get payment requirements that need to be blocked.
        
        Returns payments past block_due that are still active or warned.
        """
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(PlexPaymentRequirement)
            .where(
                and_(
                    PlexPaymentRequirement.block_due < now,
                    PlexPaymentRequirement.status.in_([
                        PlexPaymentStatus.ACTIVE,
                        PlexPaymentStatus.WARNING_SENT,
                    ])
                )
            )
            .options(selectinload(PlexPaymentRequirement.user))
            .options(selectinload(PlexPaymentRequirement.deposit))
            .order_by(PlexPaymentRequirement.block_due.asc())
            .limit(limit)
        )
        return result.scalars().all()

    async def mark_paid(
        self,
        payment_id: int,
        tx_hash: str,
        amount: Decimal,
    ) -> PlexPaymentRequirement | None:
        """
        Mark payment as received.
        
        Args:
            payment_id: Payment requirement ID
            tx_hash: Transaction hash
            amount: Amount paid
            
        Returns:
            Updated payment requirement or None
        """
        payment = await self.get_by_id(payment_id)
        if not payment:
            return None
        
        payment.mark_paid(tx_hash, amount)
        await self._session.flush()
        await self._session.refresh(payment)
        
        logger.info(
            f"PLEX payment confirmed: payment_id={payment_id}, "
            f"tx_hash={tx_hash[:10]}..., amount={amount}"
        )
        
        return payment

    async def mark_warning_sent(
        self, payment_id: int
    ) -> PlexPaymentRequirement | None:
        """Mark warning as sent for a payment."""
        payment = await self.get_by_id(payment_id)
        if not payment:
            return None
        
        payment.mark_warning_sent()
        await self._session.flush()
        
        logger.warning(
            f"PLEX payment warning sent: payment_id={payment_id}, "
            f"user_id={payment.user_id}, deposit_id={payment.deposit_id}"
        )
        
        return payment

    async def mark_blocked(
        self, payment_id: int
    ) -> PlexPaymentRequirement | None:
        """Mark deposit as blocked due to non-payment."""
        payment = await self.get_by_id(payment_id)
        if not payment:
            return None
        
        payment.mark_blocked()
        await self._session.flush()
        
        logger.error(
            f"PLEX payment blocked: payment_id={payment_id}, "
            f"user_id={payment.user_id}, deposit_id={payment.deposit_id}"
        )
        
        return payment

    async def get_total_daily_plex_required(self, user_id: int) -> Decimal:
        """
        Get total daily PLEX required for all active deposits.
        
        Args:
            user_id: User ID
            
        Returns:
            Total daily PLEX required
        """
        payments = await self.get_active_by_user_id(user_id)
        total = sum(p.daily_plex_required for p in payments)
        return Decimal(str(total))

    async def delete_by_deposit_id(self, deposit_id: int) -> bool:
        """
        Delete payment requirement for a deposit.
        
        Args:
            deposit_id: Deposit ID
            
        Returns:
            True if deleted, False if not found
        """
        payment = await self.get_by_deposit_id(deposit_id)
        if not payment:
            return False
        
        await self._session.delete(payment)
        await self._session.flush()
        
        logger.info(f"Deleted PLEX payment requirement for deposit_id={deposit_id}")
        return True

    async def reset_to_active(self, payment_id: int) -> PlexPaymentRequirement | None:
        """
        Reset payment status to active (for admin use).
        
        Args:
            payment_id: Payment requirement ID
            
        Returns:
            Updated payment or None
        """
        payment = await self.get_by_id(payment_id)
        if not payment:
            return None
        
        now = datetime.now(UTC)
        payment.status = PlexPaymentStatus.ACTIVE
        payment.next_payment_due = now + timedelta(hours=24)
        payment.warning_due = now + timedelta(hours=25)
        payment.block_due = now + timedelta(hours=49)
        payment.warning_sent_at = None
        
        await self._session.flush()
        await self._session.refresh(payment)
        
        logger.info(f"Reset PLEX payment to active: payment_id={payment_id}")
        return payment

