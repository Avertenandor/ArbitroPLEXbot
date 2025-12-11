"""
Shared utilities for monitoring service.

Provides constants, helper classes, and utility functions for
data formatting, validation, and time calculations.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any


# ============================================================================
# TIME CONSTANTS
# ============================================================================

DEFAULT_LOOKBACK_HOURS = 24
"""Default lookback period for statistics in hours."""


# ============================================================================
# LIMIT CONSTANTS
# ============================================================================

MAX_LIMIT_ADMIN_ACTIONS = 100
"""Maximum number of admin actions to retrieve."""

MAX_LIMIT_USER_SEARCH = 50
"""Maximum number of users to return in search results."""

MAX_LIMIT_INQUIRIES = 100
"""Maximum number of inquiries to retrieve."""

LIMIT_TOP_ACTIONS = 5
"""Number of top action types to show."""

LIMIT_RECENT_DEPOSITS = 10
"""Number of recent deposits to show."""

LIMIT_PENDING_WITHDRAWALS = 20
"""Number of pending withdrawals to show."""

LIMIT_USER_TRANSACTIONS = 50
"""Maximum number of user transactions to retrieve."""

LIMIT_DEFAULT = 10
"""Default limit for list queries."""


# ============================================================================
# STRING CONSTANTS
# ============================================================================

STRING_TRUNCATE = 100
"""Default length for string truncation."""

DEFAULT_USERNAME = "Unknown"
"""Default username when user information is not available."""

DEFAULT_UNASSIGNED = "Не назначен"
"""Default text for unassigned items (Russian: "Not assigned")."""


# ============================================================================
# DATE FORMAT CONSTANTS
# ============================================================================

DATE_FORMAT_TIME = "%H:%M"
"""Time only format (e.g., "14:30")."""

DATE_FORMAT_SHORT = "%d.%m %H:%M"
"""Short date format with time (e.g., "25.12 14:30")."""

DATE_FORMAT_FULL = "%d.%m.%Y %H:%M"
"""Full date format with time (e.g., "25.12.2025 14:30")."""

DATE_FORMAT_DATE_ONLY = "%d.%m.%Y"
"""Date only format (e.g., "25.12.2025")."""


# ============================================================================
# STATUS CONSTANTS
# ============================================================================

STATUS_ACTIVE = "active"
"""Active status for deposits and other entities."""

STATUS_PENDING = "pending"
"""Pending status for transactions."""

STATUS_WITHDRAWAL = "withdrawal"
"""Withdrawal transaction type."""

STATUS_NEW = "new"
"""New status for inquiries."""

STATUS_IN_PROGRESS = "in_progress"
"""In progress status for inquiries."""

STATUS_CLOSED = "closed"
"""Closed status for inquiries."""


# ============================================================================
# OPTIONAL MODEL FLAGS
# ============================================================================

# Try to import optional models to determine availability
try:
    from app.models.user_inquiry import UserInquiry  # noqa: F401

    HAS_INQUIRIES = True
except ImportError:
    HAS_INQUIRIES = False

try:
    from app.models.support_ticket import SupportTicket  # noqa: F401

    HAS_TICKETS = True
except ImportError:
    HAS_TICKETS = False

try:
    from app.models.user_activity import UserActivity  # noqa: F401

    HAS_ACTIVITY = True
except ImportError:
    HAS_ACTIVITY = False


# ============================================================================
# TIME HELPER CLASS
# ============================================================================


class TimeHelper:
    """Helper class for time calculations and manipulations."""

    @staticmethod
    def get_since(hours: int) -> datetime:
        """
        Get datetime for N hours ago from now (UTC).

        Args:
            hours: Number of hours to subtract

        Returns:
            Datetime object for N hours ago in UTC

        Example:
            >>> TimeHelper.get_since(24)  # 24 hours ago
            datetime.datetime(2025, 12, 10, 15, 30, 0, tzinfo=datetime.UTC)
        """
        return datetime.now(UTC) - timedelta(hours=hours)

    @staticmethod
    def get_today_start() -> datetime:
        """
        Get datetime for today at 00:00:00 UTC.

        Returns:
            Datetime object for today's start in UTC

        Example:
            >>> TimeHelper.get_today_start()
            datetime.datetime(2025, 12, 11, 0, 0, 0, tzinfo=datetime.UTC)
        """
        return datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def get_since_days(days: int) -> datetime:
        """
        Get datetime for N days ago from now (UTC).

        Args:
            days: Number of days to subtract

        Returns:
            Datetime object for N days ago in UTC

        Example:
            >>> TimeHelper.get_since_days(7)  # 7 days ago
            datetime.datetime(2025, 12, 4, 15, 30, 0, tzinfo=datetime.UTC)
        """
        return datetime.now(UTC) - timedelta(days=days)

    @staticmethod
    def get_now() -> datetime:
        """
        Get current datetime in UTC.

        Returns:
            Current datetime object in UTC

        Example:
            >>> TimeHelper.get_now()
            datetime.datetime(2025, 12, 11, 15, 30, 0, tzinfo=datetime.UTC)
        """
        return datetime.now(UTC)


# ============================================================================
# FORMAT HELPER CLASS
# ============================================================================


class FormatHelper:
    """Helper class for data formatting and conversion."""

    @staticmethod
    def format_datetime(
        dt: datetime | None,
        fmt: str = DATE_FORMAT_SHORT,
    ) -> str:
        """
        Format datetime object to string.

        Args:
            dt: Datetime object to format (can be None)
            fmt: Format string (default: DATE_FORMAT_SHORT)

        Returns:
            Formatted datetime string, or empty string if dt is None

        Example:
            >>> dt = datetime(2025, 12, 11, 15, 30)
            >>> FormatHelper.format_datetime(dt)
            "11.12 15:30"
            >>> FormatHelper.format_datetime(dt, DATE_FORMAT_FULL)
            "11.12.2025 15:30"
            >>> FormatHelper.format_datetime(None)
            ""
        """
        if dt is None:
            return ""
        return dt.strftime(fmt)

    @staticmethod
    def truncate_text(
        text: str | None,
        max_length: int = STRING_TRUNCATE,
        suffix: str = "...",
    ) -> str:
        """
        Truncate text to maximum length with suffix.

        Args:
            text: Text to truncate (can be None)
            max_length: Maximum length (default: STRING_TRUNCATE)
            suffix: Suffix to append if truncated (default: "...")

        Returns:
            Truncated text with suffix if needed, or empty string if text is None

        Example:
            >>> FormatHelper.truncate_text("Short text", 100)
            "Short text"
            >>> FormatHelper.truncate_text("A very long text" * 10, 20)
            "A very long textA ve..."
            >>> FormatHelper.truncate_text(None)
            ""
        """
        if text is None:
            return ""
        if len(text) <= max_length:
            return text
        return text[:max_length] + suffix

    @staticmethod
    def safe_float(
        value: Any,
        default: float = 0.0,
    ) -> float:
        """
        Safely convert value to float with default fallback.

        Args:
            value: Value to convert
            default: Default value if conversion fails (default: 0.0)

        Returns:
            Float value or default if conversion fails

        Example:
            >>> FormatHelper.safe_float("123.45")
            123.45
            >>> FormatHelper.safe_float("invalid", 0.0)
            0.0
            >>> FormatHelper.safe_float(None, 10.0)
            10.0
        """
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def safe_decimal_to_float(
        value: Decimal | None,
        default: float = 0.0,
    ) -> float:
        """
        Safely convert Decimal to float with default fallback.

        Args:
            value: Decimal value to convert (can be None)
            default: Default value if conversion fails (default: 0.0)

        Returns:
            Float value or default if value is None

        Example:
            >>> from decimal import Decimal
            >>> FormatHelper.safe_decimal_to_float(Decimal("123.45"))
            123.45
            >>> FormatHelper.safe_decimal_to_float(None, 0.0)
            0.0
        """
        if value is None:
            return default
        return float(value)

    @staticmethod
    def safe_username(username: str | None) -> str:
        """
        Get username or default if None.

        Args:
            username: Username (can be None)

        Returns:
            Username or DEFAULT_USERNAME if None

        Example:
            >>> FormatHelper.safe_username("john_doe")
            "john_doe"
            >>> FormatHelper.safe_username(None)
            "Unknown"
        """
        return username or DEFAULT_USERNAME

    @staticmethod
    def format_amount(amount: float | Decimal, decimals: int = 2) -> str:
        """
        Format amount with thousand separators.

        Args:
            amount: Amount to format
            decimals: Number of decimal places (default: 2)

        Returns:
            Formatted amount string

        Example:
            >>> FormatHelper.format_amount(1234.56)
            "1,234.56"
            >>> FormatHelper.format_amount(1000000, 0)
            "1,000,000"
        """
        if isinstance(amount, Decimal):
            amount = float(amount)
        return f"{amount:,.{decimals}f}"


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================


def validate_limit(
    value: int,
    default: int = LIMIT_DEFAULT,
    max_value: int = MAX_LIMIT_ADMIN_ACTIONS,
) -> int:
    """
    Validate and clamp limit value to acceptable range.

    Args:
        value: Limit value to validate
        default: Default value if invalid (default: LIMIT_DEFAULT)
        max_value: Maximum allowed value (default: MAX_LIMIT_ADMIN_ACTIONS)

    Returns:
        Validated limit value (clamped to 1..max_value)

    Example:
        >>> validate_limit(50)
        50
        >>> validate_limit(0, default=10)
        10
        >>> validate_limit(-5, default=10)
        10
        >>> validate_limit(200, max_value=100)
        100
    """
    if value is None or value < 1:
        return default
    if value > max_value:
        return max_value
    return value


def validate_hours(
    value: int,
    default: int = DEFAULT_LOOKBACK_HOURS,
    max_hours: int = 720,
) -> int:
    """
    Validate and clamp hours value to acceptable range.

    Args:
        value: Hours value to validate
        default: Default value if invalid (default: DEFAULT_LOOKBACK_HOURS)
        max_hours: Maximum allowed hours (default: 720 = 30 days)

    Returns:
        Validated hours value (clamped to 1..max_hours)

    Example:
        >>> validate_hours(24)
        24
        >>> validate_hours(0, default=24)
        24
        >>> validate_hours(1000, max_hours=720)
        720
    """
    if value is None or value < 1:
        return default
    if value > max_hours:
        return max_hours
    return value
