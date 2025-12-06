"""
Tests for reward amount calculation.

Tests the core reward calculation formula:
(deposit_amount * rate * days) / 100

Covers:
- Basic reward calculation
- Multiple days calculation
- Edge cases (zero values, negative values)
- Precision testing
- Large amounts
"""

from decimal import Decimal


class TestRewardAmountCalculation:
    """Test reward amount calculation."""

    def test_calculate_basic_reward(self, calculator):
        """Test basic reward calculation."""
        # Formula: (deposit_amount * rate * days) / 100
        # Example: (1000 * 1.117 * 1) / 100 = 11.17
        result = calculator.calculate_reward_amount(
            Decimal("1000"),
            Decimal("1.117"),
            days=1
        )
        assert result == Decimal("11.17")

    def test_calculate_reward_multiple_days(self, calculator):
        """Test reward calculation for multiple days."""
        result = calculator.calculate_reward_amount(
            Decimal("1000"),
            Decimal("1.117"),
            days=7
        )
        expected = Decimal("1000") * Decimal("1.117") * 7 / 100
        assert result == expected

    def test_calculate_reward_zero_rate(self, calculator):
        """Test reward with zero rate."""
        result = calculator.calculate_reward_amount(
            Decimal("1000"),
            Decimal("0"),
            days=1
        )
        assert result == Decimal("0")

    def test_calculate_reward_zero_amount(self, calculator):
        """Test reward with zero amount."""
        result = calculator.calculate_reward_amount(
            Decimal("0"),
            Decimal("1.117"),
            days=1
        )
        assert result == Decimal("0")

    def test_calculate_reward_negative_amount(self, calculator):
        """Test reward with negative amount returns zero."""
        result = calculator.calculate_reward_amount(
            Decimal("-1000"),
            Decimal("1.117"),
            days=1
        )
        assert result == Decimal("0")

    def test_calculate_reward_negative_rate(self, calculator):
        """Test reward with negative rate returns zero."""
        result = calculator.calculate_reward_amount(
            Decimal("1000"),
            Decimal("-1.117"),
            days=1
        )
        assert result == Decimal("0")

    def test_calculate_reward_zero_days(self, calculator):
        """Test reward with zero days returns zero."""
        result = calculator.calculate_reward_amount(
            Decimal("1000"),
            Decimal("1.117"),
            days=0
        )
        assert result == Decimal("0")

    def test_calculate_reward_negative_days(self, calculator):
        """Test reward with negative days returns zero."""
        result = calculator.calculate_reward_amount(
            Decimal("1000"),
            Decimal("1.117"),
            days=-1
        )
        assert result == Decimal("0")

    def test_calculate_reward_high_rate(self, calculator):
        """Test reward with high rate."""
        result = calculator.calculate_reward_amount(
            Decimal("1000"),
            Decimal("10.0"),
            days=1
        )
        assert result == Decimal("100.00")

    def test_calculate_reward_low_rate(self, calculator):
        """Test reward with low rate."""
        result = calculator.calculate_reward_amount(
            Decimal("1000"),
            Decimal("0.01"),
            days=1
        )
        assert result == Decimal("0.10")

    def test_calculate_reward_precision(self, calculator):
        """Test reward calculation maintains precision."""
        result = calculator.calculate_reward_amount(
            Decimal("1000.123"),
            Decimal("1.117"),
            days=1
        )
        expected = (Decimal("1000.123") * Decimal("1.117")) / 100
        assert result == expected

    def test_calculate_reward_large_amount(self, calculator):
        """Test reward with large deposit amount."""
        result = calculator.calculate_reward_amount(
            Decimal("1000000"),
            Decimal("1.117"),
            days=1
        )
        assert result == Decimal("11170.00")
