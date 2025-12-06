"""
Tests for minimum PLEX balance logic.

Tests the concept of "non-withdrawable reserve" (5000 PLEX minimum)
and "available balance" (balance above minimum that can be spent).
"""

from decimal import Decimal

import pytest

from bot.constants.rules import (
    MINIMUM_PLEX_BALANCE,
    can_spend_plex,
    get_available_plex_balance,
    get_balance_after_spending,
)


class TestMinimumPlexBalance:
    """Tests for minimum PLEX balance constants and functions."""

    def test_minimum_plex_balance_is_5000(self):
        """Verify minimum PLEX balance is 5000."""
        assert MINIMUM_PLEX_BALANCE == 5000

    def test_get_available_balance_above_minimum(self):
        """Test available balance when above minimum."""
        # User has 7000 PLEX, minimum is 5000
        # Available should be 2000
        total = 7000
        available = get_available_plex_balance(total)
        assert available == Decimal("2000")

    def test_get_available_balance_at_minimum(self):
        """Test available balance when exactly at minimum."""
        # User has exactly 5000 PLEX (minimum)
        # Available should be 0
        total = 5000
        available = get_available_plex_balance(total)
        assert available == Decimal("0")

    def test_get_available_balance_below_minimum(self):
        """Test available balance when below minimum."""
        # User has 3000 PLEX, minimum is 5000
        # Available should be 0 (not negative)
        total = 3000
        available = get_available_plex_balance(total)
        assert available == Decimal("0")

    def test_get_available_balance_zero(self):
        """Test available balance when balance is zero."""
        total = 0
        available = get_available_plex_balance(total)
        assert available == Decimal("0")

    def test_get_available_balance_with_decimal(self):
        """Test available balance works with Decimal input."""
        total = Decimal("10000.50")
        available = get_available_plex_balance(total)
        assert available == Decimal("5000.50")

    def test_get_available_balance_large_amount(self):
        """Test available balance with large balance."""
        total = 100000
        available = get_available_plex_balance(total)
        assert available == Decimal("95000")


class TestCanSpendPlex:
    """Tests for can_spend_plex function."""

    def test_can_spend_when_sufficient(self):
        """Test spending is allowed when sufficient available balance."""
        # User has 7000 PLEX (2000 available)
        # Wants to spend 1000 -> should be allowed
        assert can_spend_plex(7000, 1000) is True

    def test_can_spend_exact_available(self):
        """Test spending exact available amount is allowed."""
        # User has 7000 PLEX (2000 available)
        # Wants to spend 2000 -> should be allowed
        assert can_spend_plex(7000, 2000) is True

    def test_cannot_spend_more_than_available(self):
        """Test spending more than available is not allowed."""
        # User has 7000 PLEX (2000 available)
        # Wants to spend 3000 -> should be denied
        assert can_spend_plex(7000, 3000) is False

    def test_cannot_spend_at_minimum(self):
        """Test no spending allowed when at minimum balance."""
        # User has exactly 5000 PLEX (0 available)
        # Any spending should be denied
        assert can_spend_plex(5000, 10) is False

    def test_cannot_spend_below_minimum(self):
        """Test no spending allowed when below minimum."""
        # User has 3000 PLEX (0 available)
        # Any spending should be denied
        assert can_spend_plex(3000, 10) is False

    def test_can_spend_zero(self):
        """Test spending zero is always allowed."""
        assert can_spend_plex(7000, 0) is True
        assert can_spend_plex(5000, 0) is True
        assert can_spend_plex(3000, 0) is True

    def test_can_spend_with_decimal(self):
        """Test spending with Decimal values."""
        # User has 10000.5 PLEX (5000.5 available)
        # Spending 5000.5 should be allowed
        assert can_spend_plex(Decimal("10000.5"), Decimal("5000.5")) is True
        # Spending 5001 should be denied
        assert can_spend_plex(Decimal("10000.5"), Decimal("5001")) is False


class TestGetBalanceAfterSpending:
    """Tests for get_balance_after_spending function."""

    def test_valid_spending_returns_correct_balance(self):
        """Test balance calculation after valid spending."""
        # User has 7000 PLEX, spends 1000
        # Balance after: 6000, is_valid: True (>= 5000)
        balance_after, is_valid = get_balance_after_spending(7000, 1000)
        assert balance_after == Decimal("6000")
        assert is_valid is True

    def test_spending_to_minimum_is_valid(self):
        """Test spending down to minimum is valid."""
        # User has 7000 PLEX, spends 2000
        # Balance after: 5000, is_valid: True (== 5000)
        balance_after, is_valid = get_balance_after_spending(7000, 2000)
        assert balance_after == Decimal("5000")
        assert is_valid is True

    def test_spending_below_minimum_is_invalid(self):
        """Test spending below minimum is invalid."""
        # User has 7000 PLEX, spends 3000
        # Balance after: 4000, is_valid: False (< 5000)
        balance_after, is_valid = get_balance_after_spending(7000, 3000)
        assert balance_after == Decimal("4000")
        assert is_valid is False

    def test_spending_from_below_minimum_is_invalid(self):
        """Test spending from below minimum is invalid."""
        # User has 3000 PLEX, spends 100
        # Balance after: 2900, is_valid: False (< 5000)
        balance_after, is_valid = get_balance_after_spending(3000, 100)
        assert balance_after == Decimal("2900")
        assert is_valid is False


class TestDepositPaymentScenarios:
    """Real-world scenarios for deposit payments (10 PLEX per $1 deposit)."""

    def test_can_afford_small_deposit_payment(self):
        """Test user can afford payment for $100 deposit."""
        # User has 6000 PLEX (1000 available)
        # Daily payment for $100 deposit: 1000 PLEX
        total_plex = 6000
        daily_payment = 100 * 10  # $100 * 10 PLEX/$ = 1000 PLEX

        assert can_spend_plex(total_plex, daily_payment) is True

    def test_cannot_afford_large_deposit_payment(self):
        """Test user cannot afford payment for $500 deposit with insufficient available."""
        # User has 6000 PLEX (1000 available)
        # Daily payment for $500 deposit: 5000 PLEX
        total_plex = 6000
        daily_payment = 500 * 10  # $500 * 10 PLEX/$ = 5000 PLEX

        assert can_spend_plex(total_plex, daily_payment) is False

    def test_exact_available_for_deposit(self):
        """Test user can afford deposit payment when exactly matching available."""
        # User has 6000 PLEX (1000 available)
        # Daily payment for $100 deposit: 1000 PLEX (exactly available)
        total_plex = 6000
        daily_payment = 100 * 10

        assert can_spend_plex(total_plex, daily_payment) is True


class TestAuthorizationPaymentScenarios:
    """Scenarios for authorization payment (10 PLEX)."""

    def test_can_afford_auth_payment(self):
        """Test user can afford 10 PLEX auth payment."""
        # User has 5020 PLEX (20 available)
        # Auth payment: 10 PLEX
        total_plex = 5020
        auth_payment = 10

        assert can_spend_plex(total_plex, auth_payment) is True

    def test_cannot_afford_auth_payment_at_minimum(self):
        """Test user at minimum cannot afford auth payment."""
        # User has exactly 5000 PLEX (0 available)
        # Auth payment: 10 PLEX
        total_plex = 5000
        auth_payment = 10

        assert can_spend_plex(total_plex, auth_payment) is False

    def test_cannot_afford_auth_with_5_plex_available(self):
        """Test user with 5 PLEX available cannot afford 10 PLEX auth."""
        # User has 5005 PLEX (5 available)
        # Auth payment: 10 PLEX
        total_plex = 5005
        auth_payment = 10

        assert can_spend_plex(total_plex, auth_payment) is False


class TestMultiplePaymentsScenario:
    """Test scenarios with multiple payments."""

    def test_calculate_available_after_multiple_deposits(self):
        """Test calculating available for user with multiple deposits."""
        # User has 15000 PLEX (10000 available)
        # Has 3 deposits totaling $500 = 5000 PLEX/day
        # After daily payment: 10000 available
        total_plex = 15000
        available = get_available_plex_balance(total_plex)
        daily_payment = 500 * 10

        assert available == Decimal("10000")
        assert can_spend_plex(total_plex, daily_payment) is True

        # Check balance after
        balance_after, is_valid = get_balance_after_spending(total_plex, daily_payment)
        assert balance_after == Decimal("10000")  # 15000 - 5000 = 10000
        assert is_valid is True  # 10000 >= 5000
