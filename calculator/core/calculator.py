"""
Pure business logic calculator for profitability calculations.

This module contains standalone calculation logic without any
dependencies on database, ORM, or app-specific code.
"""

from decimal import Decimal
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from calculator.core.models import CalculationResult, DepositCalculation, DepositLevel


class ProfitabilityCalculator:
    """
    Pure business logic calculator for deposit rewards and ROI tracking.

    This class provides standalone calculation methods that work with
    pure data types (Decimal) without any external dependencies.
    """

    def calculate_daily_reward(
        self,
        amount: Decimal,
        rate_percent: Decimal
    ) -> Decimal:
        """
        Calculate daily reward for a given amount and rate.

        Formula: (amount * rate_percent) / 100

        Args:
            amount: Deposit amount
            rate_percent: Daily reward rate as percentage (e.g., 1.1170 = 1.117%)

        Returns:
            Daily reward amount

        Example:
            >>> calc = ProfitabilityCalculator()
            >>> calc.calculate_daily_reward(Decimal("1000"), Decimal("1.1170"))
            Decimal('11.17000')
        """
        if amount <= 0:
            return Decimal("0")

        if rate_percent < 0:
            return Decimal("0")

        return (amount * rate_percent) / 100

    def calculate_period_reward(
        self,
        amount: Decimal,
        rate_percent: Decimal,
        days: int
    ) -> Decimal:
        """
        Calculate reward for a specific period of days.

        Formula: (amount * rate_percent * days) / 100

        Args:
            amount: Deposit amount
            rate_percent: Daily reward rate as percentage
            days: Number of days to calculate for

        Returns:
            Total reward amount for the period

        Example:
            >>> calc = ProfitabilityCalculator()
            >>> calc.calculate_period_reward(Decimal("1000"), Decimal("1.1170"), 30)
            Decimal('335.10000')
        """
        if amount <= 0:
            return Decimal("0")

        if rate_percent < 0:
            return Decimal("0")

        if days <= 0:
            return Decimal("0")

        return (amount * rate_percent * days) / 100

    def calculate_roi_cap(
        self,
        amount: Decimal,
        cap_percent: Decimal
    ) -> Decimal:
        """
        Calculate total ROI cap amount based on deposit and cap percentage.

        Formula: amount * (cap_percent / 100)

        Args:
            amount: Deposit amount
            cap_percent: ROI cap as percentage (e.g., 500 = 500%)

        Returns:
            Total ROI cap amount

        Example:
            >>> calc = ProfitabilityCalculator()
            >>> calc.calculate_roi_cap(Decimal("1000"), Decimal("500"))
            Decimal('5000.00')
        """
        if amount <= 0:
            return Decimal("0")

        if cap_percent < 0:
            return Decimal("0")

        return amount * (cap_percent / 100)

    def calculate_remaining_roi(
        self,
        roi_cap: Decimal,
        roi_paid: Decimal
    ) -> Decimal:
        """
        Calculate remaining ROI space available.

        Formula: roi_cap - roi_paid

        Args:
            roi_cap: Total ROI cap amount
            roi_paid: Amount already paid out

        Returns:
            Remaining ROI space (minimum 0)

        Example:
            >>> calc = ProfitabilityCalculator()
            >>> calc.calculate_remaining_roi(Decimal("5000"), Decimal("500"))
            Decimal('4500')
        """
        if roi_cap <= 0:
            return Decimal("0")

        remaining = roi_cap - roi_paid
        return max(remaining, Decimal("0"))

    def is_roi_cap_reached(
        self,
        roi_paid: Decimal,
        roi_cap: Decimal
    ) -> bool:
        """
        Check if ROI cap has been reached.

        Args:
            roi_paid: Amount already paid out
            roi_cap: Total ROI cap amount

        Returns:
            True if cap is reached, False otherwise

        Example:
            >>> calc = ProfitabilityCalculator()
            >>> calc.is_roi_cap_reached(Decimal("5000"), Decimal("5000"))
            True
            >>> calc.is_roi_cap_reached(Decimal("4999"), Decimal("5000"))
            False
        """
        if roi_cap <= 0:
            return False

        return roi_paid >= roi_cap

    def cap_reward_to_remaining(
        self,
        reward: Decimal,
        remaining: Decimal
    ) -> Decimal:
        """
        Cap reward amount to remaining ROI space.

        Ensures that the reward doesn't exceed the remaining ROI cap.

        Args:
            reward: Original calculated reward amount
            remaining: Remaining ROI space available

        Returns:
            Capped reward (minimum of reward and remaining)

        Example:
            >>> calc = ProfitabilityCalculator()
            >>> calc.cap_reward_to_remaining(Decimal("100"), Decimal("50"))
            Decimal('50')
            >>> calc.cap_reward_to_remaining(Decimal("100"), Decimal("150"))
            Decimal('100')
        """
        if reward <= 0:
            return Decimal("0")

        if remaining <= 0:
            return Decimal("0")

        return min(reward, remaining)

    def calculate_days_to_cap(
        self,
        amount: Decimal,
        rate_percent: Decimal,
        cap_percent: Decimal
    ) -> int:
        """
        Calculate number of days until ROI cap is reached.

        Formula: (cap_percent / rate_percent)

        Args:
            amount: Deposit amount
            rate_percent: Daily reward rate as percentage
            cap_percent: ROI cap as percentage

        Returns:
            Number of days until cap (rounded up)

        Example:
            >>> calc = ProfitabilityCalculator()
            >>> calc.calculate_days_to_cap(
            ...     Decimal("1000"),
            ...     Decimal("1.1170"),
            ...     Decimal("500")
            ... )
            448
        """
        if amount <= 0:
            return 0

        if rate_percent <= 0:
            return 0

        if cap_percent <= 0:
            return 0

        # Calculate number of days: cap_percent / rate_percent
        # This is independent of amount since both numerator and denominator
        # would be multiplied by amount
        days_decimal = cap_percent / rate_percent

        # Round up to get full days
        import math
        return math.ceil(days_decimal)

    def calculate_full_projection(
        self,
        amount: Decimal,
        rate_percent: Decimal,
        cap_percent: Decimal,
    ) -> "CalculationResult":
        """
        Calculate full ROI projection for a deposit.

        Args:
            amount: Deposit amount
            rate_percent: Daily ROI percentage
            cap_percent: ROI cap percentage

        Returns:
            CalculationResult with all projections

        Example:
            >>> calc = ProfitabilityCalculator()
            >>> result = calc.calculate_full_projection(
            ...     Decimal("1000"),
            ...     Decimal("1.117"),
            ...     Decimal("500")
            ... )
            >>> result.daily_reward
            Decimal('11.17')
        """
        from calculator.core.models import CalculationResult

        daily = self.calculate_daily_reward(amount, rate_percent)
        roi_cap = self.calculate_roi_cap(amount, cap_percent)
        days_to_cap = self.calculate_days_to_cap(amount, rate_percent, cap_percent)

        return CalculationResult(
            daily_reward=daily,
            weekly_reward=daily * 7,
            monthly_reward=daily * 30,
            yearly_reward=daily * 365,
            roi_cap_amount=roi_cap,
            days_to_cap=days_to_cap,
        )

    def calculate_for_level(
        self,
        amount: Decimal,
        level: "DepositLevel",
    ) -> "DepositCalculation":
        """
        Calculate projection for a specific deposit level.

        Args:
            amount: Deposit amount
            level: DepositLevel configuration

        Returns:
            DepositCalculation with level and results

        Raises:
            ValueError: If amount is below level minimum
        """
        from calculator.core.models import DepositCalculation

        if amount < level.min_amount:
            raise ValueError(
                f"Amount {amount} is below level minimum {level.min_amount}"
            )

        result = self.calculate_full_projection(
            amount=amount,
            rate_percent=level.roi_percent,
            cap_percent=level.roi_cap_percent,
        )

        return DepositCalculation(
            amount=amount,
            level=level,
            result=result,
        )
