"""
Input validation functions for AI tool executor.

Provides consistent validation and sanitization of tool input parameters.
All validators raise ValueError on invalid input.
"""

from decimal import Decimal, InvalidOperation
from typing import Any


__all__ = [
    "validate_required_string",
    "validate_optional_string",
    "validate_positive_int",
    "validate_positive_decimal",
    "validate_user_identifier",
    "validate_limit",
    "validate_enum",
    "validate_boolean",
]


def validate_required_string(value: Any, field_name: str, max_length: int = 1000) -> str:
    """
    Validate and sanitize a required string field.

    Args:
        value: The value to validate
        field_name: Name of the field (for error messages)
        max_length: Maximum allowed length (default: 1000)

    Returns:
        Sanitized string value

    Raises:
        ValueError: If value is None, empty, or invalid

    Example:
        >>> validate_required_string("hello", "message")
        'hello'
        >>> validate_required_string("", "message")
        ValueError: message cannot be empty
    """
    if value is None:
        raise ValueError(f"{field_name} is required")
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} cannot be empty")
    if len(value) > max_length:
        value = value[:max_length]
    return value


def validate_optional_string(value: Any, field_name: str, max_length: int = 1000) -> str | None:
    """
    Validate and sanitize an optional string field.

    Args:
        value: The value to validate
        field_name: Name of the field (for error messages)
        max_length: Maximum allowed length (default: 1000)

    Returns:
        Sanitized string value or None if empty/None

    Example:
        >>> validate_optional_string("hello", "note")
        'hello'
        >>> validate_optional_string(None, "note")
        None
        >>> validate_optional_string("", "note")
        None
    """
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if not value:
        return None
    if len(value) > max_length:
        value = value[:max_length]
    return value


def validate_positive_int(value: Any, field_name: str, max_value: int = 1000000) -> int:
    """
    Validate a positive integer field.

    Args:
        value: The value to validate
        field_name: Name of the field (for error messages)
        max_value: Maximum allowed value (default: 1000000)

    Returns:
        Validated integer value (capped at max_value)

    Raises:
        ValueError: If value is None, not an integer, or not positive

    Example:
        >>> validate_positive_int(42, "count")
        42
        >>> validate_positive_int(-5, "count")
        ValueError: count must be positive
        >>> validate_positive_int(2000000, "count", max_value=1000000)
        1000000
    """
    if value is None:
        raise ValueError(f"{field_name} is required")
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be an integer")
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")
    if value > max_value:
        value = max_value
    return value


def validate_positive_decimal(value: Any, field_name: str, max_value: Decimal = Decimal("1000000000")) -> Decimal:
    """
    Validate a positive decimal field.

    Args:
        value: The value to validate
        field_name: Name of the field (for error messages)
        max_value: Maximum allowed value (default: Decimal("1000000000"))

    Returns:
        Validated Decimal value

    Raises:
        ValueError: If value is None, not a number, not positive, or exceeds max_value

    Example:
        >>> validate_positive_decimal("123.45", "amount")
        Decimal('123.45')
        >>> validate_positive_decimal(-10, "amount")
        ValueError: amount must be positive
    """
    if value is None:
        raise ValueError(f"{field_name} is required")
    try:
        value = Decimal(str(value))
    except (TypeError, ValueError, InvalidOperation):
        raise ValueError(f"{field_name} must be a number")
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")
    if value > max_value:
        raise ValueError(f"{field_name} exceeds maximum allowed value")
    return value


def validate_user_identifier(value: Any, field_name: str = "user_identifier") -> str:
    """
    Validate a user identifier (telegram_id or @username).

    Accepts:
    - Numeric Telegram ID (e.g., "123456789")
    - Username with @ prefix (e.g., "@username")
    - Username without @ prefix (e.g., "username")

    Args:
        value: The value to validate
        field_name: Name of the field (for error messages, default: "user_identifier")

    Returns:
        Validated user identifier string

    Raises:
        ValueError: If value is None, empty, or invalid format

    Example:
        >>> validate_user_identifier("123456789")
        '123456789'
        >>> validate_user_identifier("@username")
        '@username'
        >>> validate_user_identifier("username")
        'username'
        >>> validate_user_identifier("@")
        ValueError: user_identifier: invalid username format
    """
    if value is None:
        raise ValueError(f"{field_name} is required")
    value = str(value).strip()
    if not value:
        raise ValueError(f"{field_name} cannot be empty")
    # Accept: numeric ID, @username, or plain username
    if value.startswith("@"):
        if len(value) < 2:
            raise ValueError(f"{field_name}: invalid username format")
    elif not value.isdigit():
        # Allow alphanumeric usernames without @
        if not all(c.isalnum() or c == "_" for c in value):
            raise ValueError(f"{field_name}: invalid format")
    return value


def validate_limit(value: Any, default: int = 20, max_limit: int = 100) -> int:
    """
    Validate a limit parameter for pagination/queries.

    Args:
        value: The value to validate
        default: Default value if None or invalid (default: 20)
        max_limit: Maximum allowed limit (default: 100)

    Returns:
        Validated limit value (between 1 and max_limit)

    Example:
        >>> validate_limit(10)
        10
        >>> validate_limit(None)
        20
        >>> validate_limit(500, max_limit=100)
        100
        >>> validate_limit(-5)
        20
    """
    if value is None:
        return default
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    if value <= 0:
        return default
    if value > max_limit:
        return max_limit
    return value


def validate_enum(value: Any, field_name: str, allowed_values: set[str]) -> str:
    """
    Validate that a value is one of the allowed enum values.

    Args:
        value: The value to validate
        field_name: Name of the field (for error messages)
        allowed_values: Set of allowed string values

    Returns:
        Validated string value

    Raises:
        ValueError: If value is None, empty, or not in allowed_values

    Example:
        >>> validate_enum("add", "operation", {"add", "subtract", "set"})
        'add'
        >>> validate_enum("invalid", "operation", {"add", "subtract"})
        ValueError: operation must be one of: add, subtract
    """
    if value is None:
        raise ValueError(f"{field_name} is required")
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} cannot be empty")
    if value not in allowed_values:
        allowed = ", ".join(sorted(allowed_values))
        raise ValueError(f"{field_name} must be one of: {allowed}")
    return value


def validate_boolean(value: Any, field_name: str) -> bool:
    """
    Validate and convert a value to boolean.

    Accepts:
    - Python bool: True/False
    - Integers: 0 (False), 1 (True)
    - Strings: "true"/"false", "yes"/"no", "1"/"0" (case-insensitive)

    Args:
        value: The value to validate
        field_name: Name of the field (for error messages)

    Returns:
        Boolean value

    Raises:
        ValueError: If value is None or cannot be converted to boolean

    Example:
        >>> validate_boolean(True, "enabled")
        True
        >>> validate_boolean("yes", "enabled")
        True
        >>> validate_boolean(0, "enabled")
        False
        >>> validate_boolean("invalid", "enabled")
        ValueError: enabled must be a boolean value
    """
    if value is None:
        raise ValueError(f"{field_name} is required")

    # Handle boolean type
    if isinstance(value, bool):
        return value

    # Handle integer
    if isinstance(value, int):
        if value in (0, 1):
            return bool(value)
        raise ValueError(f"{field_name} must be a boolean value (got integer: {value})")

    # Handle string
    if isinstance(value, str):
        value_lower = value.strip().lower()
        if value_lower in ("true", "yes", "1", "on"):
            return True
        if value_lower in ("false", "no", "0", "off"):
            return False
        raise ValueError(f"{field_name} must be a boolean value (got: '{value}')")

    raise ValueError(f"{field_name} must be a boolean value (got type: {type(value).__name__})")
