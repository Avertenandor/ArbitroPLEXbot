"""
Common validators for user input.

Each validator returns a tuple of (is_valid, parsed_value, error_message).
"""

import re
from decimal import Decimal, InvalidOperation

from app.utils.validation import normalize_bsc_address, validate_bsc_address


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
    if not value or not isinstance(value, str):
        return False, None, "Wallet address cannot be empty"

    value = value.strip()

    if not value:
        return False, None, "Wallet address cannot be empty"

    # Check basic format
    if not value.startswith("0x"):
        return False, None, "Wallet address must start with '0x'"

    if len(value) != 42:
        return (
            False,
            None,
            "Wallet address must be 42 characters long (0x + 40 hex chars)",
        )

    # Validate using existing validation function
    if not validate_bsc_address(value, checksum=False):
        return False, None, "Invalid wallet address format"

    # Normalize to checksum format
    try:
        normalized = normalize_bsc_address(value)
        return True, normalized, None
    except ValueError as e:
        return False, None, f"Invalid wallet address: {e}"


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
    if not value or not isinstance(value, str):
        return False, None, "Amount cannot be empty"

    value = value.strip()

    if not value:
        return False, None, "Amount cannot be empty"

    # Replace comma with dot for decimal separator
    value = value.replace(",", ".")

    # Try to parse as Decimal
    try:
        amount = Decimal(value)
    except (InvalidOperation, ValueError):
        return False, None, "Amount must be a valid number"

    # Check if amount is finite
    if not amount.is_finite():
        return False, None, "Amount must be a finite number"

    # Check minimum amount
    if amount < min_amount:
        return (
            False,
            None,
            f"Amount must be greater than or equal to {min_amount}",
        )

    # Check for reasonable precision (8 decimal places max)
    if amount.as_tuple().exponent < -8:
        return (
            False,
            None,
            "Amount has too many decimal places (maximum 8)",
        )

    return True, amount, None


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
    if not value or not isinstance(value, str):
        return False, None, "Email cannot be empty"

    value = value.strip()

    if not value:
        return False, None, "Email cannot be empty"

    # Check length
    if len(value) > 255:
        return False, None, "Email is too long (maximum 255 characters)"

    # Check for @
    if "@" not in value:
        return False, None, "Email must contain '@'"

    # Split local and domain parts
    parts = value.split("@")
    if len(parts) != 2:
        return False, None, "Email must contain exactly one '@'"

    local, domain = parts

    # Check local part
    if not local or len(local) > 64:
        return (
            False,
            None,
            "Email local part must be 1-64 characters",
        )

    # Check domain part
    if not domain or len(domain) < 3:
        return False, None, "Email domain is too short"

    # Check for dot in domain
    if "." not in domain:
        return False, None, "Email domain must contain a dot (.)"

    # Check domain has valid structure
    domain_parts = domain.split(".")
    if any(not part for part in domain_parts):
        return False, None, "Email domain has invalid structure"

    # Basic regex validation
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, value):
        return (
            False,
            None,
            "Email format is invalid. Expected: user@example.com",
        )

    # Normalize to lowercase
    normalized = value.lower()

    return True, normalized, None


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
    if not value or not isinstance(value, str):
        return False, None, "Phone number cannot be empty"

    value = value.strip()

    if not value:
        return False, None, "Phone number cannot be empty"

    # Check length before cleaning
    if len(value) > 50:
        return False, None, "Phone number is too long (maximum 50 characters)"

    # Clean phone: remove spaces, dashes, parentheses
    cleaned = (
        value.replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
        .replace(".", "")
    )

    # Check if cleaned value contains only digits and optional leading +
    if cleaned.startswith("+"):
        digits = cleaned[1:]
        if not digits.isdigit():
            return (
                False,
                None,
                "Phone number must contain only digits after '+'",
            )
    else:
        if not cleaned.isdigit():
            return False, None, "Phone number must contain only digits"

    # Check minimum length (10 digits)
    digits_only = cleaned.lstrip("+")
    if len(digits_only) < 10:
        return (
            False,
            None,
            "Phone number is too short (minimum 10 digits)",
        )

    # Check maximum length (15 digits, international standard)
    if len(digits_only) > 15:
        return (
            False,
            None,
            "Phone number is too long (maximum 15 digits)",
        )

    return True, cleaned, None
