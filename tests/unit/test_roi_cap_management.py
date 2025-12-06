"""
Tests for ROI cap management.

Tests cover:
- ROI cap calculation (based on deposit amount and multiplier)
- ROI cap reached detection
- Capping rewards to remaining ROI

These tests ensure the system correctly enforces ROI limits
and prevents over-payment to users.
"""

from decimal import Decimal


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
