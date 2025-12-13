"""
Helper functions for bonus management v2.

This module contains utility and validation functions extracted from
bonus_management_v2.py, providing reusable logic for bonus operations.
"""

from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

from bot.utils.text_utils import escape_markdown

from .constants import (
    BONUS_MAX_AMOUNT,
    BONUS_MIN_AMOUNT,
    BONUS_ROI_CAP_MULTIPLIER,
    ROLE_DISPLAY,
    ROLE_PERMISSIONS,
)

if TYPE_CHECKING:
    from app.models.bonus_credit import BonusCredit


# ============ STATUS HELPERS ============


def get_bonus_status(bonus: "BonusCredit") -> str:
    """
    Get status string from BonusCredit model.

    Model has: is_active, is_roi_completed, cancelled_at
    Returns: "active", "completed", "cancelled", or "inactive"
    """
    if bonus.cancelled_at is not None:
        return "cancelled"
    if bonus.is_roi_completed:
        return "completed"
    if bonus.is_active:
        return "active"
    return "inactive"


def get_bonus_status_emoji(bonus: "BonusCredit") -> str:
    """Get status emoji for bonus."""
    status = get_bonus_status(bonus)
    status_map = {
        "active": "🟢",
        "completed": "✅",
        "cancelled": "❌",
        "inactive": "⚪"
    }
    return status_map.get(status, "⚪")


# ============ ROLE HELPERS ============


def get_role_display(role: str) -> str:
    """Получить отображаемое имя роли."""
    return ROLE_DISPLAY.get(role, role)


def get_role_permissions(role: str) -> dict:
    """Получить права роли."""
    default_permissions = {
        "can_grant": False,
        "can_view": False,
        "can_cancel_any": False,
        "can_cancel_own": False
    }
    return ROLE_PERMISSIONS.get(role, default_permissions)


# ============ VALIDATION FUNCTIONS ============


def validate_amount(amount_str: str) -> tuple[Decimal | None, str | None]:
    """
    Validate bonus amount string.

    Parses amount from string, handles "USDT" suffix and commas,
    validates against min/max constraints.

    Args:
        amount_str: String representation of amount (e.g., "100", "50.5 USDT", "1,000")

    Returns:
        Tuple of (amount, error_message):
        - On success: (Decimal amount, None)
        - On failure: (None, error message string)

    Examples:
        >>> validate_amount("100")
        (Decimal('100'), None)
        >>> validate_amount("50.5 USDT")
        (Decimal('50.5'), None)
        >>> validate_amount("0.5")
        (None, "Минимальная сумма: 1 USDT")
        >>> validate_amount("invalid")
        (None, "Неверный формат суммы")
    """
    # Clean up the input string
    cleaned = amount_str.replace("USDT", "").replace(",", ".").strip()

    try:
        amount = Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None, "Неверный формат суммы. Введите число от 1 до 100,000"

    # Validate range
    if amount < BONUS_MIN_AMOUNT:
        return None, f"Минимальная сумма: {BONUS_MIN_AMOUNT} USDT"

    if amount > BONUS_MAX_AMOUNT:
        return None, f"Максимальная сумма: {BONUS_MAX_AMOUNT:,} USDT"

    return amount, None


def validate_reason(reason: str) -> tuple[str | None, str | None]:
    """
    Validate bonus reason string.

    Checks length constraints (5-200 characters) and strips whitespace.

    Args:
        reason: The reason text to validate

    Returns:
        Tuple of (cleaned_reason, error_message):
        - On success: (stripped reason string, None)
        - On failure: (None, error message string)

    Examples:
        >>> validate_reason("Welcome bonus")
        ("Welcome bonus", None)
        >>> validate_reason("  VIP  ")
        ("VIP", None)
        >>> validate_reason("abc")
        (None, "Причина слишком короткая. Минимум 5 символов.")
        >>> validate_reason("a" * 250)
        (None, "Причина слишком длинная. Максимум 200 символов.")
    """
    cleaned = reason.strip()

    if len(cleaned) < 5:
        return None, "Причина слишком короткая. Минимум 5 символов."

    if len(cleaned) > 200:
        return None, "Причина слишком длинная. Максимум 200 символов."

    return cleaned, None


# ============ CALCULATION HELPERS ============


def calculate_roi_cap(amount: Decimal) -> Decimal:
    """
    Calculate ROI cap for bonus amount.

    The ROI cap is the maximum total ROI that can be earned from a bonus,
    calculated as amount × BONUS_ROI_CAP_MULTIPLIER (typically 5x = 500%).

    Args:
        amount: The bonus amount

    Returns:
        The ROI cap amount (amount × multiplier)

    Example:
        >>> calculate_roi_cap(Decimal("100"))
        Decimal('500')
    """
    return amount * BONUS_ROI_CAP_MULTIPLIER


# ============ FORMATTING HELPERS ============


def format_user_display(user) -> str:
    """
    Format user display name with proper escaping.

    Returns escaped username with @ prefix, or falls back to "ID:{telegram_id}"
    if username is not available.

    Args:
        user: User model object with username and telegram_id attributes

    Returns:
        Escaped display string for markdown

    Examples:
        >>> format_user_display(user_with_username)
        "@escaped\\_username"
        >>> format_user_display(user_without_username)
        "ID:123456789"
    """
    if user.username:
        return f"@{escape_markdown(user.username)}"
    return f"ID:{user.telegram_id}"


def truncate_reason(reason: str, max_len: int = 25) -> str:
    """
    Truncate reason string with ellipsis if too long.

    Args:
        reason: The reason text to truncate
        max_len: Maximum length before truncation (default: 25)

    Returns:
        Truncated string with "..." suffix if needed

    Examples:
        >>> truncate_reason("Short reason")
        "Short reason"
        >>> truncate_reason("This is a very long reason that needs truncating", max_len=20)
        "This is a very long ..."
    """
    if len(reason) <= max_len:
        return reason
    return reason[:max_len] + "..."
