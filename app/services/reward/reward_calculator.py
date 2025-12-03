"""
Reward calculator.

Encapsulates reward calculation logic for deposits and ROI tracking.
"""

from decimal import Decimal

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deposit import Deposit


class RewardCalculator:
    """
    Reward calculator for deposit rewards and ROI tracking.

    This class extracts all calculation logic from RewardService
    to provide a single source of truth for reward computations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize reward calculator.

        Args:
            session: Database session
        """
        self.session = session

    def calculate_reward_amount(
        self, deposit_amount: Decimal, rate: Decimal, days: int = 1
    ) -> Decimal:
        """
        Calculate reward amount based on deposit amount and rate.

        Formula: (deposit_amount * rate * days) / 100

        Args:
            deposit_amount: Deposit amount
            rate: Reward rate as percentage (e.g., 1.1170 = 1.117%)
            days: Number of days (default 1)

        Returns:
            Calculated reward amount

        Example:
            >>> calc = RewardCalculator(session)
            >>> calc.calculate_reward_amount(Decimal("1000"), Decimal("1.1170"), 1)
            Decimal("11.17")
        """
        if deposit_amount <= 0:
            logger.warning(
                "Invalid deposit amount for reward calculation",
                extra={"deposit_amount": str(deposit_amount)}
            )
            return Decimal("0")

        if rate < 0:
            logger.warning(
                "Invalid rate for reward calculation",
                extra={"rate": str(rate)}
            )
            return Decimal("0")

        if days <= 0:
            logger.warning(
                "Invalid days for reward calculation",
                extra={"days": days}
            )
            return Decimal("0")

        # Calculate reward: (amount * rate * days) / 100
        reward_amount = (deposit_amount * rate * days) / 100

        return reward_amount

    def calculate_roi_cap(
        self, deposit_amount: Decimal, multiplier: Decimal
    ) -> Decimal:
        """
        Calculate ROI cap amount based on deposit amount and multiplier.

        Formula: deposit_amount * (multiplier / 100)

        Args:
            deposit_amount: Deposit amount
            multiplier: ROI cap multiplier as percentage (e.g., 500 = 500%)

        Returns:
            Calculated ROI cap amount

        Example:
            >>> calc = RewardCalculator(session)
            >>> calc.calculate_roi_cap(Decimal("1000"), Decimal("500"))
            Decimal("5000.00")
        """
        if deposit_amount <= 0:
            logger.warning(
                "Invalid deposit amount for ROI cap calculation",
                extra={"deposit_amount": str(deposit_amount)}
            )
            return Decimal("0")

        if multiplier < 0:
            logger.warning(
                "Invalid multiplier for ROI cap calculation",
                extra={"multiplier": str(multiplier)}
            )
            return Decimal("0")

        # Calculate ROI cap: amount * (multiplier / 100)
        roi_cap = deposit_amount * (multiplier / 100)

        return roi_cap

    def calculate_remaining_roi(
        self, deposit: Deposit, total_earned: Decimal | None = None
    ) -> Decimal:
        """
        Calculate remaining ROI space for a deposit.

        Formula: roi_cap_amount - roi_paid_amount

        Args:
            deposit: Deposit object
            total_earned: Optional override for total earned amount
                         (if None, uses deposit.roi_paid_amount)

        Returns:
            Remaining ROI space

        Example:
            >>> calc = RewardCalculator(session)
            >>> calc.calculate_remaining_roi(deposit)
            Decimal("4500.00")
        """
        if not deposit.roi_cap_amount:
            logger.warning(
                "Deposit has no ROI cap amount",
                extra={"deposit_id": deposit.id}
            )
            return Decimal("0")

        # Use provided total_earned or deposit's roi_paid_amount
        earned = total_earned if total_earned is not None else (
            deposit.roi_paid_amount or Decimal("0")
        )

        # Calculate remaining: roi_cap - roi_paid
        roi_remaining = deposit.roi_cap_amount - earned

        # Ensure non-negative
        return max(roi_remaining, Decimal("0"))

    async def get_rate_for_level(
        self, level: int, session_id: int | None = None
    ) -> Decimal:
        """
        Get reward rate for a deposit level.

        Priority:
        1. RewardSession rate (if session_id provided and rate > 0)
        2. Otherwise returns 0 (caller should use deposit_version rate)

        Args:
            level: Deposit level (1-5)
            session_id: Optional reward session ID

        Returns:
            Reward rate as Decimal (percentage)

        Raises:
            ValueError: If level not in range 1-5
        """
        if level < 1 or level > 5:
            raise ValueError(f"Level must be 1-5, got {level}")

        # If no session_id, return 0 (use deposit version rate)
        if session_id is None:
            return Decimal("0")

        # Get RewardSession
        from app.repositories.reward_session_repository import (
            RewardSessionRepository,
        )

        session_repo = RewardSessionRepository(self.session)
        reward_session = await session_repo.get_by_id(session_id)

        if not reward_session:
            logger.warning(
                "RewardSession not found",
                extra={"session_id": session_id}
            )
            return Decimal("0")

        # Get rate for level
        try:
            rate = reward_session.get_reward_rate_for_level(level)
            return rate
        except ValueError as e:
            logger.error(
                f"Failed to get rate for level: {e}",
                extra={"session_id": session_id, "level": level}
            )
            return Decimal("0")

    def is_roi_cap_reached(
        self, deposit: Deposit, total_earned: Decimal | None = None
    ) -> bool:
        """
        Check if ROI cap has been reached for a deposit.

        Args:
            deposit: Deposit object
            total_earned: Optional override for total earned amount
                         (if None, uses deposit.roi_paid_amount)

        Returns:
            True if ROI cap reached, False otherwise

        Example:
            >>> calc = RewardCalculator(session)
            >>> calc.is_roi_cap_reached(deposit)
            False
        """
        if not deposit.roi_cap_amount:
            logger.warning(
                "Deposit has no ROI cap amount",
                extra={"deposit_id": deposit.id}
            )
            return False

        # Use provided total_earned or deposit's roi_paid_amount
        earned = total_earned if total_earned is not None else (
            deposit.roi_paid_amount or Decimal("0")
        )

        # Check if cap reached
        cap_reached = earned >= deposit.roi_cap_amount

        if cap_reached:
            logger.info(
                "ROI cap reached",
                extra={
                    "deposit_id": deposit.id,
                    "roi_paid": str(earned),
                    "roi_cap": str(deposit.roi_cap_amount),
                }
            )

        return cap_reached

    def cap_reward_to_remaining_roi(
        self, reward_amount: Decimal, deposit: Deposit
    ) -> Decimal:
        """
        Cap reward amount to remaining ROI space.

        This is a convenience method that combines calculate_remaining_roi
        with a minimum check to ensure reward doesn't exceed ROI cap.

        Args:
            reward_amount: Original calculated reward amount
            deposit: Deposit object

        Returns:
            Capped reward amount (minimum of reward_amount and remaining ROI)

        Example:
            >>> calc = RewardCalculator(session)
            >>> calc.cap_reward_to_remaining_roi(Decimal("100"), deposit)
            Decimal("100.00")  # or less if remaining ROI < 100
        """
        if not deposit.roi_cap_amount:
            # No cap, return original amount
            return reward_amount

        # Calculate remaining ROI
        roi_remaining = self.calculate_remaining_roi(deposit)

        # Cap to remaining
        if reward_amount > roi_remaining:
            logger.warning(
                "Reward capped to remaining ROI",
                extra={
                    "deposit_id": deposit.id,
                    "level": deposit.level,
                    "original_reward": str(reward_amount),
                    "capped_reward": str(roi_remaining),
                }
            )
            return roi_remaining

        return reward_amount
