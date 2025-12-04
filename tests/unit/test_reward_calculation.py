"""
Unit tests for reward calculation logic.

Tests cover:
- Reward amount calculation
- ROI cap calculation
- ROI progress tracking
- Remaining ROI calculation
- Edge cases for financial calculations
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.reward.reward_calculator import RewardCalculator


@pytest.fixture
def mock_session():
    """Mock async session."""
    session = AsyncMock()
    return session


@pytest.fixture
def calculator(mock_session):
    """Create RewardCalculator instance."""
    return RewardCalculator(mock_session)


@pytest.fixture
def mock_deposit():
    """Create mock deposit object."""
    deposit = MagicMock()
    deposit.id = 1
    deposit.user_id = 100
    deposit.amount = Decimal("1000")
    deposit.level = 1
    deposit.roi_cap_amount = Decimal("5000")  # 500% cap
    deposit.roi_paid_amount = Decimal("0")
    deposit.is_roi_completed = False
    return deposit


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


class TestROICapCalculation:
    """Test ROI cap calculation."""

    def test_calculate_roi_cap_500_percent(self, calculator):
        """Test ROI cap at 500%."""
        result = calculator.calculate_roi_cap(
            Decimal("1000"),
            Decimal("500")
        )
        assert result == Decimal("5000.00")

    def test_calculate_roi_cap_100_percent(self, calculator):
        """Test ROI cap at 100%."""
        result = calculator.calculate_roi_cap(
            Decimal("1000"),
            Decimal("100")
        )
        assert result == Decimal("1000.00")

    def test_calculate_roi_cap_zero_multiplier(self, calculator):
        """Test ROI cap with zero multiplier."""
        result = calculator.calculate_roi_cap(
            Decimal("1000"),
            Decimal("0")
        )
        assert result == Decimal("0")

    def test_calculate_roi_cap_zero_amount(self, calculator):
        """Test ROI cap with zero amount."""
        result = calculator.calculate_roi_cap(
            Decimal("0"),
            Decimal("500")
        )
        assert result == Decimal("0")

    def test_calculate_roi_cap_negative_amount(self, calculator):
        """Test ROI cap with negative amount returns zero."""
        result = calculator.calculate_roi_cap(
            Decimal("-1000"),
            Decimal("500")
        )
        assert result == Decimal("0")

    def test_calculate_roi_cap_negative_multiplier(self, calculator):
        """Test ROI cap with negative multiplier returns zero."""
        result = calculator.calculate_roi_cap(
            Decimal("1000"),
            Decimal("-500")
        )
        assert result == Decimal("0")

    def test_calculate_roi_cap_large_amount(self, calculator):
        """Test ROI cap with large amount."""
        result = calculator.calculate_roi_cap(
            Decimal("1000000"),
            Decimal("500")
        )
        assert result == Decimal("5000000.00")

    def test_calculate_roi_cap_decimal_amount(self, calculator):
        """Test ROI cap with decimal amount."""
        result = calculator.calculate_roi_cap(
            Decimal("1000.50"),
            Decimal("500")
        )
        assert result == Decimal("5002.50")


class TestRemainingROICalculation:
    """Test remaining ROI calculation."""

    def test_calculate_remaining_roi_no_payments(self, calculator, mock_deposit):
        """Test remaining ROI with no payments."""
        mock_deposit.roi_paid_amount = Decimal("0")

        result = calculator.calculate_remaining_roi(mock_deposit)

        assert result == Decimal("5000")

    def test_calculate_remaining_roi_partial_payment(self, calculator, mock_deposit):
        """Test remaining ROI with partial payment."""
        mock_deposit.roi_paid_amount = Decimal("2500")  # 50% paid

        result = calculator.calculate_remaining_roi(mock_deposit)

        assert result == Decimal("2500")

    def test_calculate_remaining_roi_almost_complete(self, calculator, mock_deposit):
        """Test remaining ROI when almost complete."""
        mock_deposit.roi_paid_amount = Decimal("4999")

        result = calculator.calculate_remaining_roi(mock_deposit)

        assert result == Decimal("1")

    def test_calculate_remaining_roi_complete(self, calculator, mock_deposit):
        """Test remaining ROI when cap reached."""
        mock_deposit.roi_paid_amount = Decimal("5000")

        result = calculator.calculate_remaining_roi(mock_deposit)

        assert result == Decimal("0")

    def test_calculate_remaining_roi_exceeded(self, calculator, mock_deposit):
        """Test remaining ROI when cap exceeded (should return 0)."""
        mock_deposit.roi_paid_amount = Decimal("6000")

        result = calculator.calculate_remaining_roi(mock_deposit)

        assert result == Decimal("0")  # Should not be negative

    def test_calculate_remaining_roi_with_override(self, calculator, mock_deposit):
        """Test remaining ROI with total_earned override."""
        mock_deposit.roi_paid_amount = Decimal("1000")

        result = calculator.calculate_remaining_roi(
            mock_deposit,
            total_earned=Decimal("3000")
        )

        assert result == Decimal("2000")

    def test_calculate_remaining_roi_no_cap(self, calculator, mock_deposit):
        """Test remaining ROI when deposit has no cap."""
        mock_deposit.roi_cap_amount = None

        result = calculator.calculate_remaining_roi(mock_deposit)

        assert result == Decimal("0")

    def test_calculate_remaining_roi_none_paid(self, calculator, mock_deposit):
        """Test remaining ROI when paid amount is None."""
        mock_deposit.roi_paid_amount = None

        result = calculator.calculate_remaining_roi(mock_deposit)

        assert result == Decimal("5000")


class TestROICapReached:
    """Test ROI cap reached detection."""

    def test_roi_cap_not_reached(self, calculator, mock_deposit):
        """Test ROI cap not reached."""
        mock_deposit.roi_paid_amount = Decimal("2500")

        result = calculator.is_roi_cap_reached(mock_deposit)

        assert result is False

    def test_roi_cap_exactly_reached(self, calculator, mock_deposit):
        """Test ROI cap exactly reached."""
        mock_deposit.roi_paid_amount = Decimal("5000")

        result = calculator.is_roi_cap_reached(mock_deposit)

        assert result is True

    def test_roi_cap_exceeded(self, calculator, mock_deposit):
        """Test ROI cap exceeded."""
        mock_deposit.roi_paid_amount = Decimal("6000")

        result = calculator.is_roi_cap_reached(mock_deposit)

        assert result is True

    def test_roi_cap_just_under(self, calculator, mock_deposit):
        """Test ROI cap just under limit."""
        mock_deposit.roi_paid_amount = Decimal("4999.99")

        result = calculator.is_roi_cap_reached(mock_deposit)

        assert result is False

    def test_roi_cap_with_override(self, calculator, mock_deposit):
        """Test ROI cap reached with total_earned override."""
        mock_deposit.roi_paid_amount = Decimal("1000")

        result = calculator.is_roi_cap_reached(
            mock_deposit,
            total_earned=Decimal("5000")
        )

        assert result is True

    def test_roi_cap_no_cap_amount(self, calculator, mock_deposit):
        """Test ROI cap when deposit has no cap amount."""
        mock_deposit.roi_cap_amount = None

        result = calculator.is_roi_cap_reached(mock_deposit)

        assert result is False

    def test_roi_cap_none_paid(self, calculator, mock_deposit):
        """Test ROI cap when paid amount is None."""
        mock_deposit.roi_paid_amount = None

        result = calculator.is_roi_cap_reached(mock_deposit)

        assert result is False


class TestCapRewardToRemainingROI:
    """Test capping reward to remaining ROI."""

    def test_cap_reward_within_limit(self, calculator, mock_deposit):
        """Test reward within ROI limit."""
        mock_deposit.roi_paid_amount = Decimal("4000")
        reward = Decimal("100")

        result = calculator.cap_reward_to_remaining_roi(reward, mock_deposit)

        assert result == Decimal("100")

    def test_cap_reward_exceeds_limit(self, calculator, mock_deposit):
        """Test reward that exceeds ROI limit."""
        mock_deposit.roi_paid_amount = Decimal("4950")
        reward = Decimal("100")  # Would exceed 5000 cap

        result = calculator.cap_reward_to_remaining_roi(reward, mock_deposit)

        assert result == Decimal("50")

    def test_cap_reward_exactly_fills_cap(self, calculator, mock_deposit):
        """Test reward that exactly fills ROI cap."""
        mock_deposit.roi_paid_amount = Decimal("4900")
        reward = Decimal("100")

        result = calculator.cap_reward_to_remaining_roi(reward, mock_deposit)

        assert result == Decimal("100")

    def test_cap_reward_cap_already_reached(self, calculator, mock_deposit):
        """Test reward when cap already reached."""
        mock_deposit.roi_paid_amount = Decimal("5000")
        reward = Decimal("100")

        result = calculator.cap_reward_to_remaining_roi(reward, mock_deposit)

        assert result == Decimal("0")

    def test_cap_reward_no_cap(self, calculator, mock_deposit):
        """Test reward when deposit has no cap."""
        mock_deposit.roi_cap_amount = None
        reward = Decimal("100")

        result = calculator.cap_reward_to_remaining_roi(reward, mock_deposit)

        assert result == Decimal("100")

    def test_cap_reward_very_small_remaining(self, calculator, mock_deposit):
        """Test reward with very small remaining ROI."""
        mock_deposit.roi_paid_amount = Decimal("4999.99")
        reward = Decimal("100")

        result = calculator.cap_reward_to_remaining_roi(reward, mock_deposit)

        assert result == Decimal("0.01")


class TestROIProgressCalculation:
    """Test ROI progress percentage calculation."""

    def test_roi_progress_0_percent(self):
        """Test ROI progress at 0%."""
        deposit_amount = Decimal("1000")
        roi_cap = deposit_amount * 5  # 500%
        roi_paid = Decimal("0")

        progress = (roi_paid / roi_cap * 100) if roi_cap > 0 else Decimal("0")

        assert progress == Decimal("0")

    def test_roi_progress_50_percent(self):
        """Test ROI progress at 50%."""
        deposit_amount = Decimal("1000")
        roi_cap = deposit_amount * 5
        roi_paid = Decimal("2500")

        progress = (roi_paid / roi_cap * 100)

        assert progress == Decimal("50")

    def test_roi_progress_100_percent(self):
        """Test ROI progress at 100%."""
        deposit_amount = Decimal("1000")
        roi_cap = deposit_amount * 5
        roi_paid = Decimal("5000")

        progress = (roi_paid / roi_cap * 100)

        assert progress == Decimal("100")

    def test_roi_progress_over_100_percent(self):
        """Test ROI progress over 100% (should cap at 100)."""
        deposit_amount = Decimal("1000")
        roi_cap = deposit_amount * 5
        roi_paid = Decimal("6000")

        progress = min((roi_paid / roi_cap * 100), Decimal("100"))

        assert progress == Decimal("100")

    def test_roi_progress_25_percent(self):
        """Test ROI progress at 25%."""
        deposit_amount = Decimal("1000")
        roi_cap = deposit_amount * 5
        roi_paid = Decimal("1250")

        progress = (roi_paid / roi_cap * 100)

        assert progress == Decimal("25")

    def test_roi_progress_75_percent(self):
        """Test ROI progress at 75%."""
        deposit_amount = Decimal("1000")
        roi_cap = deposit_amount * 5
        roi_paid = Decimal("3750")

        progress = (roi_paid / roi_cap * 100)

        assert progress == Decimal("75")

    def test_roi_progress_decimal_precision(self):
        """Test ROI progress with decimal precision."""
        deposit_amount = Decimal("1000")
        roi_cap = deposit_amount * 5
        roi_paid = Decimal("2345.67")

        progress = (roi_paid / roi_cap * 100)

        assert progress == Decimal("46.9134")

    def test_roi_progress_very_small(self):
        """Test ROI progress with very small payment."""
        deposit_amount = Decimal("1000")
        roi_cap = deposit_amount * 5
        roi_paid = Decimal("0.01")

        progress = (roi_paid / roi_cap * 100)

        assert progress == Decimal("0.0002")


class TestWithdrawalX5Rule:
    """Test x5 withdrawal rule (Math Validation)."""

    def test_x5_rule_within_limit(self):
        """Test withdrawal within x5 limit."""
        total_deposited = Decimal("1000")
        max_payout = total_deposited * Decimal("5.0")  # 5000
        total_withdrawn = Decimal("2000")
        withdrawal_request = Decimal("1000")

        can_withdraw = (total_withdrawn + withdrawal_request) <= max_payout

        assert can_withdraw is True

    def test_x5_rule_exactly_at_limit(self):
        """Test withdrawal exactly at x5 limit."""
        total_deposited = Decimal("1000")
        max_payout = total_deposited * Decimal("5.0")
        total_withdrawn = Decimal("4000")
        withdrawal_request = Decimal("1000")

        can_withdraw = (total_withdrawn + withdrawal_request) <= max_payout

        assert can_withdraw is True

    def test_x5_rule_exceeds_limit(self):
        """Test withdrawal that exceeds x5 limit."""
        total_deposited = Decimal("1000")
        max_payout = total_deposited * Decimal("5.0")
        total_withdrawn = Decimal("4500")
        withdrawal_request = Decimal("1000")

        can_withdraw = (total_withdrawn + withdrawal_request) <= max_payout

        assert can_withdraw is False

    def test_x5_rule_no_deposits(self):
        """Test withdrawal with no deposits."""
        total_deposited = Decimal("0")
        max_payout = total_deposited * Decimal("5.0")
        withdrawal_request = Decimal("100")

        can_withdraw = (total_deposited > 0) and (withdrawal_request <= max_payout)

        assert can_withdraw is False

    def test_x5_rule_multiple_deposits(self):
        """Test withdrawal with multiple deposits."""
        total_deposited = Decimal("10") + Decimal("50") + Decimal("100")  # 160
        max_payout = total_deposited * Decimal("5.0")  # 800
        total_withdrawn = Decimal("500")
        withdrawal_request = Decimal("200")

        can_withdraw = (total_withdrawn + withdrawal_request) <= max_payout

        assert can_withdraw is True

    def test_x5_rule_just_over_limit(self):
        """Test withdrawal just over x5 limit."""
        total_deposited = Decimal("1000")
        max_payout = total_deposited * Decimal("5.0")
        total_withdrawn = Decimal("4999")
        withdrawal_request = Decimal("2")  # Would be 5001 total

        can_withdraw = (total_withdrawn + withdrawal_request) <= max_payout

        assert can_withdraw is False

    def test_x5_rule_large_amounts(self):
        """Test x5 rule with large amounts."""
        total_deposited = Decimal("100000")
        max_payout = total_deposited * Decimal("5.0")  # 500000
        total_withdrawn = Decimal("300000")
        withdrawal_request = Decimal("150000")

        can_withdraw = (total_withdrawn + withdrawal_request) <= max_payout

        assert can_withdraw is True
