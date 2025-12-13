"""
Input validation helpers for AI tool execution.

Provides validation functions for strings, numbers, user identifiers, etc.
"""

from decimal import Decimal, InvalidOperation


def validate_required_string(
    value: str | None, field_name: str, max_length: int = 1000
) -> str:
    """Validate and sanitize a required string field."""
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


def validate_optional_string(
    value: str | None, field_name: str, max_length: int = 1000
) -> str | None:
    """Validate and sanitize an optional string field."""
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


def validate_positive_int(
    value: int | str | None, field_name: str, max_value: int = 1000000
) -> int:
    """Validate a positive integer field."""
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


def validate_positive_decimal(
    value: str | int | float | Decimal | None,
    field_name: str,
    max_value: Decimal = Decimal("1000000000"),
) -> Decimal:
    """Validate a positive decimal field."""
    if value is None:
        raise ValueError(f"{field_name} is required")
    try:
        value = Decimal(str(value))
    except (TypeError, ValueError, InvalidOperation):
        raise ValueError(f"{field_name} must be a number")
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")
    if value > max_value:
        raise ValueError(
            f"{field_name} exceeds maximum allowed value"
        )
    return value


def validate_user_identifier(
    value: str | int | None, field_name: str = "user_identifier"
) -> str:
    """Validate a user identifier (telegram_id or @username)."""
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


def validate_limit(
    value: int | str | None, default: int = 20, max_limit: int = 100
) -> int:
    """Validate a limit parameter."""
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
