"""Enhanced validation utilities."""

import re
from decimal import Decimal

from web3 import Web3

from app.validators.unified import (
    validate_wallet_address as _validate_wallet_address,
    normalize_wallet_address as _normalize_wallet_address,
)


# Zero address - used as "no wallet bound" marker
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


def is_placeholder_wallet(address: str) -> bool:
    """
    Check if wallet address is a placeholder (not a real wallet).

    Placeholder addresses are generated for users without wallets
    during import and should not be used for blockchain operations.

    Args:
        address: Wallet address to check

    Returns:
        True if address is a placeholder
    """
    if not address:
        return True

    address_lower = address.lower()

    # Check for explicit placeholder pattern
    if "placeholder" in address_lower:
        return True

    # Check for zero address (no wallet bound)
    if address_lower == ZERO_ADDRESS.lower():
        return True

    return False


def is_valid_wallet_for_transactions(address: str) -> bool:
    """
    Check if wallet address is valid for financial transactions.

    This is stricter than validate_bsc_address - it also rejects
    placeholder and zero addresses.

    Args:
        address: Wallet address to check

    Returns:
        True if address can be used for transactions
    """
    # First check if it's a placeholder
    if is_placeholder_wallet(address):
        return False

    # Then validate format
    return validate_bsc_address(address, checksum=False)


def validate_bsc_address(address: str, checksum: bool = True) -> bool:
    """
    Validate BSC wallet address.

    Args:
        address: Wallet address
        checksum: Whether to validate checksum

    Returns:
        True if valid
    """
    # Use unified validator for basic validation
    is_valid, _ = _validate_wallet_address(address)

    if not is_valid:
        return False

    # Additional checksum validation if requested
    if checksum:
        try:
            return Web3.is_checksum_address(address)
        except (ValueError, TypeError) as e:
            from loguru import logger
            logger.debug(f"Checksum validation failed for {address}: {e}")
            return False

    return True


def normalize_bsc_address(address: str) -> str:
    """
    Normalize BSC address to checksum format.

    Args:
        address: Wallet address

    Returns:
        Checksummed address

    Raises:
        ValueError: If invalid address
    """
    # Use unified normalizer
    return _normalize_wallet_address(address)


def validate_usdt_amount(
    amount: Decimal,
    min_amount: Decimal = Decimal("0.01"),
    max_amount: Decimal = Decimal("1000000"),
) -> bool:
    """
    Validate USDT amount.

    Args:
        amount: Amount to validate
        min_amount: Minimum amount
        max_amount: Maximum amount

    Returns:
        True if valid
    """
    if not isinstance(amount, Decimal):
        return False

    if amount <= 0:
        return False

    if amount < min_amount or amount > max_amount:
        return False

    return True


def validate_transaction_hash(tx_hash: str) -> bool:
    """
    Validate BSC transaction hash.

    Args:
        tx_hash: Transaction hash

    Returns:
        True if valid
    """
    if not tx_hash or not isinstance(tx_hash, str):
        return False

    # Must start with 0x and be 66 chars (0x + 64 hex chars)
    if not tx_hash.startswith("0x") or len(tx_hash) != 66:
        return False

    # Validate hex
    try:
        int(tx_hash[2:], 16)
        return True
    except ValueError:
        return False


def validate_telegram_username(username: str) -> bool:
    """
    Validate Telegram username format.

    Args:
        username: Username (with or without @)

    Returns:
        True if valid
    """
    if not username:
        return False

    # Remove @ if present
    if username.startswith("@"):
        username = username[1:]

    # Must be 5-32 chars, alphanumeric + underscore
    if len(username) < 5 or len(username) > 32:
        return False

    pattern = r"^[a-zA-Z0-9_]+$"
    return bool(re.match(pattern, username))


def sanitize_input(text: str, max_length: int = 500) -> str:
    """
    Sanitize user input.

    Args:
        text: User input
        max_length: Maximum length

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Trim whitespace
    text = text.strip()

    # Limit length
    if len(text) > max_length:
        text = text[:max_length]

    # Remove null bytes
    text = text.replace("\x00", "")

    return text
