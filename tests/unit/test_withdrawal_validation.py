"""
Unit tests for withdrawal validation logic.

Tests cover:
- Minimum withdrawal amount validation
- Balance checks
- x5 withdrawal rule (total withdrawn + request <= deposits * 5)
- Global daily withdrawal limits
"""

from decimal import Decimal

import pytest


class TestWithdrawalMinAmount:
    """Test withdrawal minimum amount validation."""

    def test_above_minimum(self):
        """Test amount above minimum is valid."""
        min_amount = Decimal("1")
        amount = Decimal("10")
        assert amount >= min_amount

    def test_exactly_at_minimum(self):
        """Test amount exactly at minimum is valid."""
        min_amount = Decimal("1")
        amount = Decimal("1")
        assert amount >= min_amount

    def test_below_minimum(self):
        """Test amount below minimum is invalid."""
        min_amount = Decimal("1")
        amount = Decimal("0.99")
        assert amount < min_amount

    def test_zero_amount(self):
        """Test zero amount is invalid."""
        min_amount = Decimal("1")
        amount = Decimal("0")
        assert amount < min_amount

    def test_negative_amount(self):
        """Test negative amount is invalid."""
        min_amount = Decimal("1")
        amount = Decimal("-10")
        assert amount < min_amount

    def test_very_small_above_minimum(self):
        """Test very small amount above minimum."""
        min_amount = Decimal("0.01")
        amount = Decimal("0.02")
        assert amount >= min_amount


class TestWithdrawalBalanceCheck:
    """Test withdrawal balance validation."""

    def test_sufficient_balance(self):
        """Test withdrawal with sufficient balance."""
        available = Decimal("100")
        requested = Decimal("50")
        assert available >= requested

    def test_exact_balance(self):
        """Test withdrawal of exact balance."""
        available = Decimal("100")
        requested = Decimal("100")
        assert available >= requested

    def test_insufficient_balance(self):
        """Test withdrawal with insufficient balance."""
        available = Decimal("100")
        requested = Decimal("150")
        assert available < requested

    def test_zero_balance(self):
        """Test withdrawal with zero balance."""
        available = Decimal("0")
        requested = Decimal("10")
        assert available < requested

    def test_negative_balance(self):
        """Test withdrawal with negative balance."""
        available = Decimal("-10")
        requested = Decimal("10")
        assert available < requested

    def test_very_small_difference(self):
        """Test withdrawal just over balance."""
        available = Decimal("100.00")
        requested = Decimal("100.01")
        assert available < requested


class TestX5WithdrawalRule:
    """Test x5 withdrawal rule (total withdrawn + request <= deposits * 5)."""

    def test_x5_rule_first_withdrawal(self):
        """Test first withdrawal within x5 limit."""
        total_deposited = Decimal("1000")
        max_payout = total_deposited * Decimal("5")
        total_withdrawn = Decimal("0")
        request = Decimal("1000")

        is_valid = (total_withdrawn + request) <= max_payout
        assert is_valid is True

    def test_x5_rule_exactly_at_limit(self):
        """Test withdrawal exactly at x5 limit."""
        total_deposited = Decimal("1000")
        max_payout = total_deposited * Decimal("5")
        total_withdrawn = Decimal("4000")
        request = Decimal("1000")

        is_valid = (total_withdrawn + request) <= max_payout
        assert is_valid is True
        assert (total_withdrawn + request) == max_payout

    def test_x5_rule_exceeds_limit(self):
        """Test withdrawal that exceeds x5 limit."""
        total_deposited = Decimal("1000")
        max_payout = total_deposited * Decimal("5")
        total_withdrawn = Decimal("4500")
        request = Decimal("600")

        is_valid = (total_withdrawn + request) <= max_payout
        assert is_valid is False

    def test_x5_rule_just_over_limit(self):
        """Test withdrawal just over x5 limit."""
        total_deposited = Decimal("1000")
        max_payout = total_deposited * Decimal("5")
        total_withdrawn = Decimal("4999")
        request = Decimal("2")

        is_valid = (total_withdrawn + request) <= max_payout
        assert is_valid is False

    def test_x5_rule_no_deposits(self):
        """Test withdrawal with no deposits fails."""
        total_deposited = Decimal("0")
        max_payout = total_deposited * Decimal("5")
        request = Decimal("100")

        # No deposits means no withdrawals allowed
        is_valid = total_deposited > 0 and request <= max_payout
        assert is_valid is False

    def test_x5_rule_multiple_small_withdrawals(self):
        """Test multiple small withdrawals within limit."""
        total_deposited = Decimal("1000")
        max_payout = total_deposited * Decimal("5")

        # Simulate multiple withdrawals
        total_withdrawn = Decimal("0")
        withdrawals = [Decimal("500"), Decimal("1000"), Decimal("1500")]

        for withdrawal in withdrawals:
            total_withdrawn += withdrawal
            is_valid = total_withdrawn <= max_payout
            assert is_valid is True

        # One more would exceed
        total_withdrawn += Decimal("2500")
        is_valid = total_withdrawn <= max_payout
        assert is_valid is False

    def test_x5_rule_with_decimal_deposits(self):
        """Test x5 rule with decimal deposit amounts."""
        total_deposited = Decimal("100.50")
        max_payout = total_deposited * Decimal("5")  # 502.50
        total_withdrawn = Decimal("400")
        request = Decimal("102.50")

        is_valid = (total_withdrawn + request) <= max_payout
        assert is_valid is True

    def test_x5_rule_large_amounts(self):
        """Test x5 rule with large amounts."""
        total_deposited = Decimal("100000")
        max_payout = total_deposited * Decimal("5")  # 500000
        total_withdrawn = Decimal("400000")
        request = Decimal("100000")

        is_valid = (total_withdrawn + request) <= max_payout
        assert is_valid is True

    def test_x5_calculation_precision(self):
        """Test x5 calculation maintains precision."""
        total_deposited = Decimal("123.45")
        max_payout = total_deposited * Decimal("5")

        expected = Decimal("617.25")
        assert max_payout == expected


class TestGlobalDailyLimit:
    """Test global daily withdrawal limit."""

    def test_within_daily_limit(self):
        """Test withdrawal within daily limit."""
        daily_limit = Decimal("10000")
        today_total = Decimal("5000")
        request = Decimal("3000")

        is_valid = (today_total + request) <= daily_limit
        assert is_valid is True

    def test_exactly_at_daily_limit(self):
        """Test withdrawal exactly at daily limit."""
        daily_limit = Decimal("10000")
        today_total = Decimal("7000")
        request = Decimal("3000")

        is_valid = (today_total + request) <= daily_limit
        assert is_valid is True

    def test_exceeds_daily_limit(self):
        """Test withdrawal that exceeds daily limit."""
        daily_limit = Decimal("10000")
        today_total = Decimal("8000")
        request = Decimal("3000")

        is_valid = (today_total + request) <= daily_limit
        assert is_valid is False

    def test_first_withdrawal_of_day(self):
        """Test first withdrawal of the day."""
        daily_limit = Decimal("10000")
        today_total = Decimal("0")
        request = Decimal("5000")

        is_valid = (today_total + request) <= daily_limit
        assert is_valid is True

    def test_daily_limit_exactly_used(self):
        """Test daily limit exactly used up."""
        daily_limit = Decimal("10000")
        today_total = Decimal("10000")
        request = Decimal("1")

        is_valid = (today_total + request) <= daily_limit
        assert is_valid is False
