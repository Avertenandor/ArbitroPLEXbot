"""
Common validators for user input.

Each validator returns a tuple of (is_valid, parsed_value, error_message).

This module provides backward-compatible wrappers around unified validators.
"""

import re
from decimal import Decimal, InvalidOperation

from app.validators.unified import (
    validate_amount as _validate_amount,
    validate_email as _validate_email,
    validate_phone as _validate_phone,
    validate_wallet_address as _validate_wallet_address,
    normalize_wallet_address,
    normalize_email as _normalize_email,
    normalize_phone as _normalize_phone,
)


def validate_telegram_id(value: str) -> tuple[bool, int | None, str | None]:
    """
    Validate Telegram ID.

    Args:
        value: String to validate as Telegram ID

    Returns:
        Tuple of (is_valid, parsed_telegram_id, error_message)

    Examples:
        >>> validate_telegram_id("123456789")
        (True, 123456789, None)
        >>> validate_telegram_id("abc")
        (False, None, "Telegram ID must be a positive integer")
        >>> validate_telegram_id("-123")
        (False, None, "Telegram ID must be a positive integer")
    """
    if not value or not isinstance(value, str):
        return False, None, "Telegram ID cannot be empty"

    value = value.strip()

    if not value:
        return False, None, "Telegram ID cannot be empty"

    # Check if it's a valid integer
    try:
        telegram_id = int(value)
    except ValueError:
        return False, None, "Telegram ID must be a positive integer"

    # Check if positive
    if telegram_id <= 0:
        return False, None, "Telegram ID must be a positive integer"

    # Telegram IDs are typically large integers (up to 10 digits)
    if telegram_id > 9999999999:  # 10 digits max
        return False, None, "Telegram ID is too large"

    return True, telegram_id, None


def validate_wallet_address(
    value: str,
) -> tuple[bool, str | None, str | None]:
    """
    Validate BSC wallet address.

    Args:
        value: String to validate as wallet address

    Returns:
        Tuple of (is_valid, normalized_address, error_message)

    Examples:
        >>> validate_wallet_address("0x1234567890123456789012345678901234567890")
        (True, "0x1234567890123456789012345678901234567890", None)
        >>> validate_wallet_address("invalid")
        (False, None, "Invalid wallet address format")
    """
    # Use unified validator
    is_valid, error = _validate_wallet_address(value)

    if not is_valid:
        return False, None, error

    # Normalize to checksum format
    try:
        normalized = normalize_wallet_address(value)
        return True, normalized, None
    except ValueError as e:
        return False, None, str(e)


def validate_amount(
    value: str, min_amount: Decimal = Decimal("0")
) -> tuple[bool, Decimal | None, str | None]:
    """
    Validate amount (USDT or other currency).

    Args:
        value: String to validate as amount
        min_amount: Minimum allowed amount (default: 0)

    Returns:
        Tuple of (is_valid, parsed_amount, error_message)

    Examples:
        >>> validate_amount("100.50")
        (True, Decimal('100.50'), None)
        >>> validate_amount("abc")
        (False, None, "Amount must be a valid number")
        >>> validate_amount("-10")
        (False, None, "Amount must be greater than or equal to 0")
    """
    # Use unified validator
    return _validate_amount(value, min_val=min_amount)


def validate_email(value: str) -> tuple[bool, str | None, str | None]:
    """
    Validate email address.

    Args:
        value: String to validate as email

    Returns:
        Tuple of (is_valid, normalized_email, error_message)

    Examples:
        >>> validate_email("user@example.com")
        (True, "user@example.com", None)
        >>> validate_email("invalid")
        (False, None, "Email must contain '@'")
    """
    # Use unified validator
    is_valid, error = _validate_email(value)

    if not is_valid:
        return False, None, error

    # Normalize to lowercase
    try:
        normalized = _normalize_email(value)
        return True, normalized, None
    except ValueError as e:
        return False, None, str(e)


def validate_phone(value: str) -> tuple[bool, str | None, str | None]:
    """
    Validate phone number.

    Args:
        value: String to validate as phone number

    Returns:
        Tuple of (is_valid, cleaned_phone, error_message)

    Examples:
        >>> validate_phone("+7 (999) 123-45-67")
        (True, "+79991234567", None)
        >>> validate_phone("123")
        (False, None, "Phone number is too short (minimum 10 digits)")
    """
    # Use unified validator
    is_valid, error = _validate_phone(value)

    if not is_valid:
        return False, None, error

    # Clean and normalize phone
    try:
        cleaned = _normalize_phone(value)
        return True, cleaned, None
    except ValueError as e:
        return False, None, str(e)
