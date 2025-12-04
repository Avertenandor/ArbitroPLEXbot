"""
Tests for standalone profitability calculator.

Tests the calculator package without database dependencies.
"""

import pytest
from decimal import Decimal

from calculator import (
    ProfitabilityCalculator,
    DepositLevel,
    CalculationResult,
    DEFAULT_LEVELS,
    get_level_by_number,
    get_level_for_amount,
    format_currency,
    format_percentage,
    format_days,
    format_days_ru,
)


class TestProfitabilityCalculator:
    """Tests for ProfitabilityCalculator class."""

    @pytest.fixture
    def calc(self) -> ProfitabilityCalculator:
        """Create calculator instance."""
        return ProfitabilityCalculator()

    # === Daily Reward Tests ===

    def test_calculate_daily_reward_basic(self, calc: ProfitabilityCalculator) -> None:
        """Test basic daily reward calculation."""
        result = calc.calculate_daily_reward(
            amount=Decimal("1000"),
            rate_percent=Decimal("1.117")
        )
        assert result == Decimal("11.17")

    def test_calculate_daily_reward_large_amount(self, calc: ProfitabilityCalculator) -> None:
        """Test daily reward with large amount."""
        result = calc.calculate_daily_reward(
            amount=Decimal("100000"),
            rate_percent=Decimal("0.8")
        )
        assert result == Decimal("800")

    def test_calculate_daily_reward_zero_amount(self, calc: ProfitabilityCalculator) -> None:
        """Test daily reward with zero amount returns zero."""
        result = calc.calculate_daily_reward(
            amount=Decimal("0"),
            rate_percent=Decimal("1.117")
        )
        assert result == Decimal("0")

    def test_calculate_daily_reward_negative_amount(self, calc: ProfitabilityCalculator) -> None:
        """Test daily reward with negative amount returns zero."""
        result = calc.calculate_daily_reward(
            amount=Decimal("-1000"),
            rate_percent=Decimal("1.117")
        )
        assert result == Decimal("0")

    def test_calculate_daily_reward_negative_rate(self, calc: ProfitabilityCalculator) -> None:
        """Test daily reward with negative rate returns zero."""
        result = calc.calculate_daily_reward(
            amount=Decimal("1000"),
            rate_percent=Decimal("-1.117")
        )
        assert result == Decimal("0")

    # === Period Reward Tests ===

    def test_calculate_period_reward_week(self, calc: ProfitabilityCalculator) -> None:
        """Test weekly reward calculation."""
        result = calc.calculate_period_reward(
            amount=Decimal("1000"),
            rate_percent=Decimal("1.117"),
            days=7
        )
        expected = Decimal("1000") * Decimal("1.117") * 7 / 100
        assert result == expected

    def test_calculate_period_reward_month(self, calc: ProfitabilityCalculator) -> None:
        """Test monthly reward calculation."""
        result = calc.calculate_period_reward(
            amount=Decimal("1000"),
            rate_percent=Decimal("1.117"),
            days=30
        )
        expected = Decimal("1000") * Decimal("1.117") * 30 / 100
        assert result == expected

    def test_calculate_period_reward_zero_days(self, calc: ProfitabilityCalculator) -> None:
        """Test period reward with zero days returns zero."""
        result = calc.calculate_period_reward(
            amount=Decimal("1000"),
            rate_percent=Decimal("1.117"),
            days=0
        )
        assert result == Decimal("0")

    # === ROI Cap Tests ===

    def test_calculate_roi_cap_500_percent(self, calc: ProfitabilityCalculator) -> None:
        """Test ROI cap at 500%."""
        result = calc.calculate_roi_cap(
            amount=Decimal("1000"),
            cap_percent=Decimal("500")
        )
        assert result == Decimal("5000")

    def test_calculate_roi_cap_large_amount(self, calc: ProfitabilityCalculator) -> None:
        """Test ROI cap with large amount."""
        result = calc.calculate_roi_cap(
            amount=Decimal("100000"),
            cap_percent=Decimal("500")
        )
        assert result == Decimal("500000")

    def test_calculate_roi_cap_zero_cap(self, calc: ProfitabilityCalculator) -> None:
        """Test ROI cap with zero percent returns zero."""
        result = calc.calculate_roi_cap(
            amount=Decimal("1000"),
            cap_percent=Decimal("0")
        )
        assert result == Decimal("0")

    # === Remaining ROI Tests ===

    def test_calculate_remaining_roi_basic(self, calc: ProfitabilityCalculator) -> None:
        """Test remaining ROI calculation."""
        result = calc.calculate_remaining_roi(
            roi_cap=Decimal("5000"),
            roi_paid=Decimal("500")
        )
        assert result == Decimal("4500")

    def test_calculate_remaining_roi_cap_reached(self, calc: ProfitabilityCalculator) -> None:
        """Test remaining ROI when cap reached."""
        result = calc.calculate_remaining_roi(
            roi_cap=Decimal("5000"),
            roi_paid=Decimal("5000")
        )
        assert result == Decimal("0")

    def test_calculate_remaining_roi_overpaid(self, calc: ProfitabilityCalculator) -> None:
        """Test remaining ROI when overpaid returns zero."""
        result = calc.calculate_remaining_roi(
            roi_cap=Decimal("5000"),
            roi_paid=Decimal("6000")
        )
        assert result == Decimal("0")

    # === ROI Cap Reached Tests ===

    def test_is_roi_cap_reached_not_reached(self, calc: ProfitabilityCalculator) -> None:
        """Test ROI cap not reached."""
        result = calc.is_roi_cap_reached(
            roi_paid=Decimal("4999"),
            roi_cap=Decimal("5000")
        )
        assert result is False

    def test_is_roi_cap_reached_exact(self, calc: ProfitabilityCalculator) -> None:
        """Test ROI cap exactly reached."""
        result = calc.is_roi_cap_reached(
            roi_paid=Decimal("5000"),
            roi_cap=Decimal("5000")
        )
        assert result is True

    def test_is_roi_cap_reached_exceeded(self, calc: ProfitabilityCalculator) -> None:
        """Test ROI cap exceeded."""
        result = calc.is_roi_cap_reached(
            roi_paid=Decimal("5001"),
            roi_cap=Decimal("5000")
        )
        assert result is True

    # === Cap Reward Tests ===

    def test_cap_reward_to_remaining_under_limit(self, calc: ProfitabilityCalculator) -> None:
        """Test capping reward when under limit."""
        result = calc.cap_reward_to_remaining(
            reward=Decimal("100"),
            remaining=Decimal("150")
        )
        assert result == Decimal("100")

    def test_cap_reward_to_remaining_over_limit(self, calc: ProfitabilityCalculator) -> None:
        """Test capping reward when over limit."""
        result = calc.cap_reward_to_remaining(
            reward=Decimal("100"),
            remaining=Decimal("50")
        )
        assert result == Decimal("50")

    def test_cap_reward_to_remaining_zero_remaining(self, calc: ProfitabilityCalculator) -> None:
        """Test capping reward when no remaining."""
        result = calc.cap_reward_to_remaining(
            reward=Decimal("100"),
            remaining=Decimal("0")
        )
        assert result == Decimal("0")

    # === Days to Cap Tests ===

    def test_calculate_days_to_cap_level1(self, calc: ProfitabilityCalculator) -> None:
        """Test days to cap for level 1."""
        result = calc.calculate_days_to_cap(
            amount=Decimal("1000"),
            rate_percent=Decimal("1.117"),
            cap_percent=Decimal("500")
        )
        # 500 / 1.117 = ~447.6 -> 448 (ceil)
        assert result == 448

    def test_calculate_days_to_cap_zero_rate(self, calc: ProfitabilityCalculator) -> None:
        """Test days to cap with zero rate."""
        result = calc.calculate_days_to_cap(
            amount=Decimal("1000"),
            rate_percent=Decimal("0"),
            cap_percent=Decimal("500")
        )
        assert result == 0

    # === Full Projection Tests ===

    def test_calculate_full_projection_level1(self, calc: ProfitabilityCalculator) -> None:
        """Test full projection for level 1."""
        result = calc.calculate_full_projection(
            amount=Decimal("1000"),
            rate_percent=Decimal("1.117"),
            cap_percent=Decimal("500")
        )

        assert isinstance(result, CalculationResult)
        assert result.daily_reward == Decimal("11.17")
        assert result.weekly_reward == Decimal("11.17") * 7
        assert result.monthly_reward == Decimal("11.17") * 30
        assert result.yearly_reward == Decimal("11.17") * 365
        assert result.roi_cap_amount == Decimal("5000")
        assert result.days_to_cap == 448

    # === Calculate for Level Tests ===

    def test_calculate_for_level(self, calc: ProfitabilityCalculator) -> None:
        """Test calculation for a deposit level."""
        level = DEFAULT_LEVELS[0]  # Level 1
        result = calc.calculate_for_level(
            amount=Decimal("1000"),
            level=level
        )

        assert result.amount == Decimal("1000")
        assert result.level == level
        assert result.result.daily_reward == Decimal("11.17")

    def test_calculate_for_level_below_minimum(self, calc: ProfitabilityCalculator) -> None:
        """Test calculation fails for amount below level minimum."""
        level = DEFAULT_LEVELS[0]  # Level 1: min 1000 USDT
        with pytest.raises(ValueError, match="below level minimum"):
            calc.calculate_for_level(
                amount=Decimal("500"),
                level=level
            )


class TestDefaultLevels:
    """Tests for default levels configuration."""

    def test_default_levels_count(self) -> None:
        """Test that there are 5 default levels."""
        assert len(DEFAULT_LEVELS) == 5

    def test_default_levels_ordering(self) -> None:
        """Test that levels are ordered by number."""
        for i, level in enumerate(DEFAULT_LEVELS):
            assert level.level_number == i + 1

    def test_get_level_by_number_exists(self) -> None:
        """Test getting existing level by number."""
        level = get_level_by_number(1)
        assert level is not None
        assert level.level_number == 1
        assert level.min_amount == Decimal("1000")

    def test_get_level_by_number_not_exists(self) -> None:
        """Test getting non-existing level returns None."""
        level = get_level_by_number(99)
        assert level is None

    def test_get_level_for_amount_exact(self) -> None:
        """Test getting level for exact minimum amount."""
        level = get_level_for_amount(Decimal("1000"))
        assert level is not None
        assert level.level_number == 1

    def test_get_level_for_amount_between(self) -> None:
        """Test getting level for amount between levels."""
        level = get_level_for_amount(Decimal("7500"))
        assert level is not None
        assert level.level_number == 2  # 5000-9999 = level 2

    def test_get_level_for_amount_below_minimum(self) -> None:
        """Test getting level for amount below minimum returns None."""
        level = get_level_for_amount(Decimal("500"))
        assert level is None


class TestFormatters:
    """Tests for formatting utilities."""

    def test_format_currency_default(self) -> None:
        """Test default currency formatting."""
        result = format_currency(Decimal("1234.56"))
        assert result == "1,234.56 USDT"

    def test_format_currency_custom_symbol(self) -> None:
        """Test currency formatting with custom symbol."""
        result = format_currency(Decimal("1234.56"), currency="$")
        assert result == "$1,234.56"

    def test_format_currency_no_decimals(self) -> None:
        """Test currency formatting without decimals."""
        result = format_currency(Decimal("1234"), decimals=0)
        assert result == "1,234 USDT"

    def test_format_percentage_default(self) -> None:
        """Test default percentage formatting."""
        result = format_percentage(Decimal("1.117"))
        assert result == "1.12%"

    def test_format_percentage_with_sign(self) -> None:
        """Test percentage formatting with sign."""
        result = format_percentage(Decimal("50"), decimals=0, show_sign=True)
        assert result == "+50%"

    def test_format_days_basic(self) -> None:
        """Test basic days formatting."""
        result = format_days(447)
        assert "447 days" in result
        assert "~15 months" in result

    def test_format_days_ru_basic(self) -> None:
        """Test Russian days formatting."""
        result = format_days_ru(447)
        assert "447 дней" in result
        assert "~15 мес." in result

    def test_format_days_ru_singular(self) -> None:
        """Test Russian singular day."""
        result = format_days_ru(1)
        assert "1 день" in result

    def test_format_days_ru_few(self) -> None:
        """Test Russian few days (2-4)."""
        result = format_days_ru(3)
        assert "3 дня" in result


class TestDepositLevelModel:
    """Tests for DepositLevel model."""

    def test_deposit_level_creation(self) -> None:
        """Test creating deposit level."""
        level = DepositLevel(
            level_number=1,
            min_amount=Decimal("1000"),
            roi_percent=Decimal("1.117"),
            roi_cap_percent=Decimal("500"),
        )
        assert level.level_number == 1
        assert level.min_amount == Decimal("1000")
        assert level.is_active is True  # default

    def test_deposit_level_validation(self) -> None:
        """Test deposit level validation."""
        with pytest.raises(ValueError):
            DepositLevel(
                level_number=0,  # Must be >= 1
                min_amount=Decimal("1000"),
                roi_percent=Decimal("1.117"),
                roi_cap_percent=Decimal("500"),
            )
