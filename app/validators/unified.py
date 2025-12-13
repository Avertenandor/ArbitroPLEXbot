"""Унифицированные валидаторы для всего проекта."""
import re
from decimal import Decimal, InvalidOperation

from web3 import Web3


def validate_wallet_address(address: str) -> tuple[bool, str | None]:
    """
    Единственный валидатор адреса кошелька.

    Args:
        address: Wallet address to validate

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid

    Examples:
        >>> validate_wallet_address("0x1234567890123456789012345678901234567890")
        (True, None)
        >>> validate_wallet_address("invalid")
        (False, "Address must start with 0x")
    """
    if not address or not isinstance(address, str):
        return False, "Address is empty"

    address = address.strip()

    if not address:
        return False, "Address is empty"

    if not address.startswith("0x"):
        return False, "Address must start with 0x"

    if len(address) != 42:
        return False, "Address must be 42 characters"

    # Validate hex format
    try:
        int(address[2:], 16)
    except ValueError:
        return False, "Invalid address format"

    # Validate using Web3 (checksum validation)
    try:
        Web3.to_checksum_address(address)
        return True, None
    except (ValueError, TypeError) as e:
        from loguru import logger
        logger.debug(f"Address validation failed for {address}: {e}")
        return False, "Invalid address format"


def validate_email(email: str) -> tuple[bool, str | None]:
    """
    Единственный валидатор email.

    Args:
        email: Email address to validate

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid

    Examples:
        >>> validate_email("user@example.com")
        (True, None)
        >>> validate_email("invalid")
        (False, "Email must contain '@'")
    """
    if not email or not isinstance(email, str):
        return False, "Email is empty"

    email = email.strip()

    if not email:
        return False, "Email is empty"

    # Check length
    if len(email) > 255:
        return False, "Email is too long (maximum 255 characters)"

    # Check for @
    if "@" not in email:
        return False, "Email must contain '@'"

    # Split local and domain parts
    parts = email.split("@")
    if len(parts) != 2:
        return False, "Email must contain exactly one '@'"

    local, domain = parts

    # Check local part
    if not local or len(local) > 64:
        return False, "Email local part must be 1-64 characters"

    # Check domain part
    if not domain or len(domain) < 3:
        return False, "Email domain is too short"

    # Check for dot in domain
    if "." not in domain:
        return False, "Email domain must contain a dot (.)"

    # Check domain has valid structure
    domain_parts = domain.split(".")
    if any(not part for part in domain_parts):
        return False, "Email domain has invalid structure"

    # Basic regex validation
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        return False, "Invalid email format"

    return True, None


def validate_phone(phone: str) -> tuple[bool, str | None]:
    """
    Единственный валидатор телефона.

    Args:
        phone: Phone number to validate

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid

    Examples:
        >>> validate_phone("+79991234567")
        (True, None)
        >>> validate_phone("123")
        (False, "Phone must be 10-15 digits")
    """
    if not phone or not isinstance(phone, str):
        return False, "Phone is empty"

    phone = phone.strip()

    if not phone:
        return False, "Phone is empty"

    # Check length before cleaning
    if len(phone) > 50:
        return False, "Phone is too long (maximum 50 characters)"

    # Remove formatting characters
    digits = re.sub(r"\D", "", phone)

    # Check digit count
    if len(digits) < 10 or len(digits) > 15:
        return False, "Phone must be 10-15 digits"

    return True, None


def validate_amount(
    amount: str,
    min_val: Decimal = Decimal("0"),
    max_val: Decimal | None = None,
) -> tuple[bool, Decimal | None, str | None]:
    """
    Единственный валидатор суммы.

    Args:
        amount: Amount string to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value (optional)

    Returns:
        Tuple of (is_valid, parsed_value, error_message)
        - (True, value, None) if valid
        - (False, None, error_message) if invalid

    Examples:
        >>> validate_amount("100.50")
        (True, Decimal('100.50'), None)
        >>> validate_amount("-10")
        (False, None, "Amount must be >= 0")
    """
    if not amount or not isinstance(amount, str):
        return False, None, "Amount is empty"

    amount = amount.strip()

    if not amount:
        return False, None, "Amount is empty"

    # Replace comma with dot
    amount = amount.replace(",", ".")

    try:
        value = Decimal(amount)
    except InvalidOperation:
        return False, None, "Invalid amount format"

    # Check if amount is finite
    if not value.is_finite():
        return False, None, "Amount must be a finite number"

    # Check minimum value
    if value < min_val:
        return False, None, f"Amount must be >= {min_val}"

    # Check maximum value
    if max_val and value > max_val:
        return False, None, f"Amount must be <= {max_val}"

    # Check precision (8 decimal places max)
    if value.as_tuple().exponent < -8:
        return False, None, "Amount has too many decimal places (maximum 8)"

    return True, value, None


# Normalization utilities (for backward compatibility)
def normalize_wallet_address(address: str) -> str:
    """
    Normalize wallet address to checksum format.

    Args:
        address: Wallet address

    Returns:
        Checksummed address

    Raises:
        ValueError: If address is invalid
    """
    is_valid, error = validate_wallet_address(address)
    if not is_valid:
        raise ValueError(error)

    return Web3.to_checksum_address(address)


def normalize_email(email: str) -> str:
    """
    Normalize email to lowercase.

    Args:
        email: Email address

    Returns:
        Lowercase email

    Raises:
        ValueError: If email is invalid
    """
    is_valid, error = validate_email(email)
    if not is_valid:
        raise ValueError(error)

    return email.strip().lower()


def normalize_phone(phone: str) -> str:
    """
    Normalize phone number by removing formatting.

    Args:
        phone: Phone number

    Returns:
        Cleaned phone number

    Raises:
        ValueError: If phone is invalid
    """
    is_valid, error = validate_phone(phone)
    if not is_valid:
        raise ValueError(error)

    # Keep + if present, remove other formatting
    cleaned = (
        phone.strip()
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
        .replace(".", "")
    )

    return cleaned
