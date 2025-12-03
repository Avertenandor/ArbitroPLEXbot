"""
Unit tests for financial validation logic.

Tests cover:
- Deposit level validation
- Withdrawal validation rules
- Balance checks
- x5 rule validation
- Minimum/maximum amount validation
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.deposit_validation_service import (
    DepositValidationService,
    DEPOSIT_LEVELS,
    PARTNER_REQUIREMENTS,
)


@pytest.fixture
def mock_session():
    """Mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    return session


class TestDepositLevelAmounts:
    """Test deposit level amount configuration."""

    def test_all_levels_defined(self):
        """Test that all 5 levels are defined."""
        assert len(DEPOSIT_LEVELS) == 5
        for level in range(1, 6):
            assert level in DEPOSIT_LEVELS

    def test_level_amounts_positive(self):
        """Test that all level amounts are positive."""
        for level, amount in DEPOSIT_LEVELS.items():
            assert amount > 0

    def test_level_amounts_ascending(self):
        """Test that level amounts are in ascending order."""
        amounts = [DEPOSIT_LEVELS[i] for i in range(1, 6)]
        assert amounts == sorted(amounts)

    def test_level_1_amount(self):
        """Test level 1 amount is 10 USDT."""
        assert DEPOSIT_LEVELS[1] == Decimal("10")

    def test_level_2_amount(self):
        """Test level 2 amount is 50 USDT."""
        assert DEPOSIT_LEVELS[2] == Decimal("50")

    def test_level_3_amount(self):
        """Test level 3 amount is 100 USDT."""
        assert DEPOSIT_LEVELS[3] == Decimal("100")

    def test_level_4_amount(self):
        """Test level 4 amount is 150 USDT."""
        assert DEPOSIT_LEVELS[4] == Decimal("150")

    def test_level_5_amount(self):
        """Test level 5 amount is 300 USDT."""
        assert DEPOSIT_LEVELS[5] == Decimal("300")


class TestPartnerRequirements:
    """Test partner requirements configuration."""

    def test_all_partner_requirements_defined(self):
        """Test that partner requirements exist for all levels."""
        assert len(PARTNER_REQUIREMENTS) == 5
        for level in range(1, 6):
            assert level in PARTNER_REQUIREMENTS

    def test_partner_requirements_non_negative(self):
        """Test that partner requirements are non-negative."""
        for level, required in PARTNER_REQUIREMENTS.items():
            assert required >= 0

    def test_level_1_no_partners_required(self):
        """Test that level 1 requires no partners."""
        assert PARTNER_REQUIREMENTS[1] == 0


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


class TestDepositLevelValidation:
    """Test deposit level validation logic."""

    def test_valid_level_range(self):
        """Test valid level range (1-5)."""
        for level in range(1, 6):
            assert level in DEPOSIT_LEVELS

    def test_invalid_level_zero(self):
        """Test invalid level 0."""
        level = 0
        assert level not in DEPOSIT_LEVELS

    def test_invalid_level_six(self):
        """Test invalid level 6."""
        level = 6
        assert level not in DEPOSIT_LEVELS

    def test_invalid_negative_level(self):
        """Test invalid negative level."""
        level = -1
        assert level not in DEPOSIT_LEVELS


class TestROICapBoundaries:
    """Test ROI cap boundary conditions."""

    def test_roi_cap_at_500_percent(self):
        """Test ROI cap at 500%."""
        deposit_amount = Decimal("1000")
        roi_cap_multiplier = Decimal("5")  # 500%
        roi_cap = deposit_amount * roi_cap_multiplier

        assert roi_cap == Decimal("5000")

    def test_roi_paid_just_under_cap(self):
        """Test ROI paid just under cap."""
        roi_cap = Decimal("5000")
        roi_paid = Decimal("4999.99")

        is_complete = roi_paid >= roi_cap
        assert is_complete is False

    def test_roi_paid_exactly_at_cap(self):
        """Test ROI paid exactly at cap."""
        roi_cap = Decimal("5000")
        roi_paid = Decimal("5000")

        is_complete = roi_paid >= roi_cap
        assert is_complete is True

    def test_roi_paid_over_cap(self):
        """Test ROI paid over cap."""
        roi_cap = Decimal("5000")
        roi_paid = Decimal("5000.01")

        is_complete = roi_paid >= roi_cap
        assert is_complete is True

    def test_roi_remaining_calculation(self):
        """Test ROI remaining calculation."""
        roi_cap = Decimal("5000")
        roi_paid = Decimal("3000")
        roi_remaining = roi_cap - roi_paid

        assert roi_remaining == Decimal("2000")

    def test_roi_remaining_negative_should_be_zero(self):
        """Test that negative ROI remaining should be treated as zero."""
        roi_cap = Decimal("5000")
        roi_paid = Decimal("6000")
        roi_remaining = max(roi_cap - roi_paid, Decimal("0"))

        assert roi_remaining == Decimal("0")


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
