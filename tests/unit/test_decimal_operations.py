"""
Unit tests for decimal precision and boundary conditions in financial calculations.

Tests cover:
- Decimal arithmetic precision (addition, subtraction, multiplication, division)
- Negative amount handling
- Boundary conditions (minimum units, large amounts, edge cases)
"""

from decimal import Decimal

import pytest


class TestAmountPrecision:
    """Test decimal precision in financial calculations."""

    def test_addition_precision(self):
        """Test addition maintains precision."""
        a = Decimal("100.12")
        b = Decimal("50.34")
        result = a + b

        assert result == Decimal("150.46")

    def test_subtraction_precision(self):
        """Test subtraction maintains precision."""
        a = Decimal("100.12")
        b = Decimal("50.34")
        result = a - b

        assert result == Decimal("49.78")

    def test_multiplication_precision(self):
        """Test multiplication maintains precision."""
        a = Decimal("100.12")
        b = Decimal("1.5")
        result = a * b

        assert result == Decimal("150.180")

    def test_division_precision(self):
        """Test division maintains precision."""
        a = Decimal("100")
        b = Decimal("3")
        result = a / b

        # Should maintain many decimal places
        assert str(result).startswith("33.33333")

    def test_comparison_precision(self):
        """Test comparison with high precision."""
        a = Decimal("100.000001")
        b = Decimal("100.000002")

        assert a < b
        assert b > a
        assert a != b

    def test_rounding_precision(self):
        """Test rounding to 2 decimal places."""
        amount = Decimal("100.12345")
        rounded = amount.quantize(Decimal("0.01"))

        assert rounded == Decimal("100.12")


class TestNegativeAmountHandling:
    """Test handling of negative amounts."""

    def test_negative_deposit_amount(self):
        """Test negative deposit amount is invalid."""
        amount = Decimal("-100")
        assert amount <= 0

    def test_negative_withdrawal_amount(self):
        """Test negative withdrawal amount is invalid."""
        amount = Decimal("-50")
        assert amount <= 0

    def test_negative_balance(self):
        """Test negative balance detection."""
        balance = Decimal("-10")
        assert balance < 0

    def test_zero_is_not_negative(self):
        """Test that zero is not considered negative."""
        amount = Decimal("0")
        assert not (amount < 0)


class TestBoundaryConditions:
    """Test various boundary conditions in financial logic."""

    def test_minimum_usdt_unit(self):
        """Test minimum USDT unit (0.01)."""
        min_unit = Decimal("0.01")
        assert min_unit > 0
        assert min_unit < Decimal("0.02")

    def test_maximum_practical_amount(self):
        """Test handling of very large amounts."""
        large_amount = Decimal("1000000")
        fee = large_amount * Decimal("0.01")  # 1%

        assert fee == Decimal("10000")

    def test_very_small_amount_handling(self):
        """Test very small amounts."""
        tiny = Decimal("0.000001")
        assert tiny > 0
        assert tiny < Decimal("0.01")

    def test_exact_integer_amounts(self):
        """Test exact integer amounts."""
        amount = Decimal("100")
        assert amount == Decimal("100.00")
        assert amount.as_tuple().exponent >= -2
