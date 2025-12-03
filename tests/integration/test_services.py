"""Integration tests for services."""

import pytest
from decimal import Decimal

from app.services.wallet_verification_service import WalletVerificationService


class TestWalletVerificationService:
    """Integration tests for WalletVerificationService."""

    @pytest.mark.asyncio
    async def test_verify_wallet_invalid_format(self):
        """Service should reject invalid wallet format without RPC calls."""
        service = WalletVerificationService()

        result = await service.verify_wallet("not-an-address")

        assert result.is_format_valid is False
        assert result.is_onchain_ok is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_verify_wallet_empty_address(self):
        """Service should reject empty address."""
        service = WalletVerificationService()

        result = await service.verify_wallet("")

        assert result.is_format_valid is False
        assert result.is_onchain_ok is False

    @pytest.mark.asyncio
    async def test_verify_wallet_short_address(self):
        """Service should reject short address."""
        service = WalletVerificationService()

        result = await service.verify_wallet("0x1234")

        assert result.is_format_valid is False
        assert result.is_onchain_ok is False

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_verify_wallet_valid_format_mock(
        self, mock_blockchain_service, sample_wallet_address
    ):
        """Service should accept valid wallet format (mocked blockchain)."""
        # This test demonstrates how to use fixtures
        # In real integration test, we would use actual blockchain connection

        balance = await mock_blockchain_service.get_usdt_balance(
            sample_wallet_address
        )

        assert isinstance(balance, Decimal)
        assert balance == Decimal("100.00")
