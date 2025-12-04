"""
Exception handling utilities.

Defines categorized exception types for proper error handling.
"""

from aiogram.exceptions import TelegramAPIError
from sqlalchemy.exc import OperationalError
from web3.exceptions import Web3Exception


class SecurityError(Exception):
    """Raised when a security-critical operation fails."""
    pass


# Exception categories based on handling strategy

# Safe to ignore - operations that fail gracefully
SAFE_TO_IGNORE = (
    TelegramAPIError,  # Message deletion, editing, etc.
)

# Must log but can continue - non-critical failures
MUST_LOG = (
    OperationalError,  # Database errors (circuit breaker handles)
    Web3Exception,     # Blockchain RPC errors (failover handles)
)

# Must raise - critical security or validation issues
MUST_RAISE = (
    ValueError,        # Validation errors
    TypeError,         # Type errors in critical paths
)


def is_safe_to_ignore(exc: Exception) -> bool:
    """
    Check if exception can be safely ignored.

    Args:
        exc: Exception to check

    Returns:
        True if exception is safe to ignore
    """
    return isinstance(exc, SAFE_TO_IGNORE)


def must_log(exc: Exception) -> bool:
    """
    Check if exception must be logged.

    Args:
        exc: Exception to check

    Returns:
        True if exception must be logged
    """
    return isinstance(exc, MUST_LOG)


def must_raise(exc: Exception) -> bool:
    """
    Check if exception must be raised.

    Args:
        exc: Exception to check

    Returns:
        True if exception must be raised
    """
    return isinstance(exc, MUST_RAISE)
