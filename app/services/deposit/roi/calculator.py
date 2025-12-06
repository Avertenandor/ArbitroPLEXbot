"""
ROI calculator module.

Handles ROI calculations and progress tracking.
"""

from decimal import Decimal

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deposit import Deposit
from app.repositories.deposit_repository import DepositRepository


class ROICalculator:
    """Calculates ROI progress and statistics."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize ROI calculator."""
        self.session = session
        self.deposit_repo = DepositRepository(session)

    async def get_level1_roi_progress(self, user_id: int) -> dict:
        """
        Get ROI progress for level 1 deposits.

        Args:
            user_id: User ID

        Returns:
            Dict with ROI progress information
        """
        deposits = await self.deposit_repo.find_by(
            user_id=user_id, level=1
        )

        if not deposits:
            return {
                "has_active_deposit": False,
                "is_completed": False,
                "deposit_amount": Decimal("0"),
                "roi_percent": 0.0,
                "roi_paid": Decimal("0"),
                "roi_remaining": Decimal("0"),
                "roi_cap": Decimal("0"),
            }

        # Get most recent deposit
        deposit = max(deposits, key=lambda d: d.created_at)

        # Calculate ROI progress
        roi_paid = getattr(deposit, "roi_paid_amount", Decimal("0"))
        roi_cap = deposit.roi_cap_amount
        roi_remaining = roi_cap - roi_paid
        roi_percent = float(roi_paid / roi_cap * 100) if roi_cap > 0 else 0.0
        is_completed = roi_paid >= roi_cap

        return {
            "has_active_deposit": True,
            "is_completed": is_completed,
            "deposit_amount": deposit.amount,
            "roi_percent": roi_percent,
            "roi_paid": roi_paid,
            "roi_remaining": roi_remaining,
            "roi_cap": roi_cap,
        }

    async def calculate_deposit_roi(self, deposit: Deposit) -> dict:
        """
        Calculate ROI for a specific deposit.

        Args:
            deposit: Deposit instance

        Returns:
            Dict with ROI calculations
        """
        roi_paid = getattr(deposit, "roi_paid_amount", Decimal("0"))
        roi_cap = deposit.roi_cap_amount
        roi_remaining = roi_cap - roi_paid
        roi_percent = float(roi_paid / roi_cap * 100) if roi_cap > 0 else 0.0
        is_completed = roi_paid >= roi_cap

        return {
            "deposit_id": deposit.id,
            "amount": deposit.amount,
            "roi_paid": roi_paid,
            "roi_cap": roi_cap,
            "roi_remaining": roi_remaining,
            "roi_percent": roi_percent,
            "is_completed": is_completed,
        }

    async def get_user_total_roi(self, user_id: int) -> dict:
        """
        Get total ROI across all user deposits.

        Args:
            user_id: User ID

        Returns:
            Dict with aggregated ROI statistics
        """
        deposits = await self.deposit_repo.get_active_deposits(user_id)

        total_invested = Decimal("0")
        total_paid = Decimal("0")
        total_cap = Decimal("0")
        total_remaining = Decimal("0")

        for deposit in deposits:
            total_invested += deposit.amount
            total_paid += getattr(deposit, "roi_paid_amount", Decimal("0"))
            total_cap += deposit.roi_cap_amount
            total_remaining += (
                deposit.roi_cap_amount -
                getattr(deposit, "roi_paid_amount", Decimal("0"))
            )

        overall_percent = (
            float(total_paid / total_cap * 100) if total_cap > 0 else 0.0
        )

        return {
            "total_deposits": len(deposits),
            "total_invested": total_invested,
            "total_paid": total_paid,
            "total_cap": total_cap,
            "total_remaining": total_remaining,
            "overall_percent": overall_percent,
        }

    async def check_roi_completion(self, deposit_id: int) -> bool:
        """
        Check if deposit ROI is completed.

        Args:
            deposit_id: Deposit ID

        Returns:
            True if ROI is completed
        """
        deposit = await self.deposit_repo.find_by_id(deposit_id)

        if not deposit:
            logger.warning(f"Deposit {deposit_id} not found for ROI check")
            return False

        roi_paid = getattr(deposit, "roi_paid_amount", Decimal("0"))
        roi_cap = deposit.roi_cap_amount

        return roi_paid >= roi_cap
