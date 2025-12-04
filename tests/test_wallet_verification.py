"""Tests for wallet validation and verification services."""

from __future__ import annotations

import pytest

from app.services.wallet_verification_service import WalletVerificationService
from app.utils.validation import validate_bsc_address


def test_validate_bsc_address_basic() -> None:
    """Validate that basic BSC address format checks work."""
    assert not validate_bsc_address("", checksum=False)
    assert not validate_bsc_address("0x1234", checksum=False)
    # 42 chars, starts with 0x, hex characters only
    valid = "0x" + "1" * 40
    assert validate_bsc_address(valid, checksum=False)


@pytest.mark.asyncio
async def test_wallet_verification_invalid_format() -> None:
    """WalletVerificationService should flag invalid addresses without RPC calls."""
    service = WalletVerificationService()

    result = await service.verify_wallet("not-an-address")

    assert result.is_format_valid is False
    assert result.is_onchain_ok is False
    assert result.error is not None
