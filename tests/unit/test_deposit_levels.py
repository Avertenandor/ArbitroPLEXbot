"""
Unit tests for deposit level configuration and validation.

Tests cover:
- Deposit level amounts (1-5)
- Partner requirements per level
- Deposit level validation rules
"""

from decimal import Decimal

import pytest

from app.services.deposit_validation_service import (
    DEPOSIT_LEVELS,
    PARTNER_REQUIREMENTS,
)


class TestDepositLevelAmounts:
    """Test deposit level amount configuration."""

    def test_all_levels_defined(self):
        """Test that all levels are defined (including test level 0)."""
        assert len(DEPOSIT_LEVELS) == 6
        for level in range(0, 6):
            assert level in DEPOSIT_LEVELS

    def test_level_amounts_positive(self):
        """Test that all level amounts are positive."""
        for level, amount in DEPOSIT_LEVELS.items():
            assert amount > 0

    def test_level_amounts_ascending(self):
        """Test that level amounts are in ascending order."""
        amounts = [DEPOSIT_LEVELS[i] for i in range(0, 6)]
        assert amounts == sorted(amounts)

    def test_test_level_amount(self):
        """Test test level (0) minimum amount is 30 USDT."""
        assert DEPOSIT_LEVELS[0] == Decimal("30")

    def test_level_1_amount(self):
        """Test level 1 minimum amount is 100 USDT."""
        assert DEPOSIT_LEVELS[1] == Decimal("100")

    def test_level_2_amount(self):
        """Test level 2 minimum amount is 700 USDT."""
        assert DEPOSIT_LEVELS[2] == Decimal("700")

    def test_level_3_amount(self):
        """Test level 3 minimum amount is 1400 USDT."""
        assert DEPOSIT_LEVELS[3] == Decimal("1400")

    def test_level_4_amount(self):
        """Test level 4 minimum amount is 2500 USDT."""
        assert DEPOSIT_LEVELS[4] == Decimal("2500")

    def test_level_5_amount(self):
        """Test level 5 minimum amount is 4000 USDT."""
        assert DEPOSIT_LEVELS[5] == Decimal("4000")


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


class TestDepositLevelValidation:
    """Test deposit level validation logic."""

    def test_valid_level_range(self):
        """Test valid level range (0-5)."""
        for level in range(0, 6):
            assert level in DEPOSIT_LEVELS

    def test_invalid_level_six(self):
        """Test invalid level 6."""
        level = 6
        assert level not in DEPOSIT_LEVELS

    def test_invalid_negative_level(self):
        """Test invalid negative level."""
        level = -1
        assert level not in DEPOSIT_LEVELS
