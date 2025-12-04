"""
Datetime utilities.

Provides timezone-aware datetime functions.
"""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """
    Get current UTC datetime with timezone info.

    Returns:
        Current datetime in UTC with timezone awareness
    """
    return datetime.now(UTC)
