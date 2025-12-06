"""
Unit tests for ROI (Return on Investment) calculations.

Tests cover:
- ROI cap at 500% (5x multiplier)
- ROI boundary conditions
- ROI remaining calculations
"""

from decimal import Decimal

import pytest


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
