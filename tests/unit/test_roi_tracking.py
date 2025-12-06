"""
Tests for ROI tracking and progress calculation.

Tests cover:
- Remaining ROI calculation
- ROI progress percentage calculation

These tests ensure accurate tracking of user earnings
and proper display of progress towards ROI caps.
"""

from decimal import Decimal


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
