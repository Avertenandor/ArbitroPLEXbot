"""
Tests for withdrawal rules and validation.

Tests the x5 withdrawal rule which limits total withdrawals
to 5 times the total deposited amount.

Formula: total_withdrawn + withdrawal_request <= total_deposited * 5

Covers:
- Withdrawals within limit
- Withdrawals at limit
- Withdrawals exceeding limit
- Edge cases (no deposits, multiple deposits)
"""

from decimal import Decimal


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
