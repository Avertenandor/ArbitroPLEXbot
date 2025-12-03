"""Unit tests for validation utilities."""

import pytest

from app.utils.validation import validate_bsc_address


class TestBSCAddressValidation:
    """Tests for BSC address validation."""

    def test_empty_address_invalid(self):
        """Empty address should be invalid."""
        assert not validate_bsc_address("", checksum=False)

    def test_short_address_invalid(self):
        """Short address should be invalid."""
        assert not validate_bsc_address("0x1234", checksum=False)

    def test_no_0x_prefix_invalid(self):
        """Address without 0x prefix should be invalid."""
        address = "1" * 40
        assert not validate_bsc_address(address, checksum=False)

    def test_valid_address_format(self):
        """Valid address format should pass."""
        # 42 chars, starts with 0x, hex characters only
        valid = "0x" + "1" * 40
        assert validate_bsc_address(valid, checksum=False)

    def test_invalid_hex_characters(self):
        """Address with non-hex characters should be invalid."""
        invalid = "0x" + "z" * 40
        assert not validate_bsc_address(invalid, checksum=False)

    def test_too_long_address(self):
        """Address longer than 42 characters should be invalid."""
        too_long = "0x" + "1" * 41
        assert not validate_bsc_address(too_long, checksum=False)

    @pytest.mark.parametrize(
        "address",
        [
            "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
            "0x0000000000000000000000000000000000000000",
            "0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF",
        ],
    )
    def test_valid_addresses(self, address):
        """Various valid address formats should pass."""
        assert validate_bsc_address(address, checksum=False)
