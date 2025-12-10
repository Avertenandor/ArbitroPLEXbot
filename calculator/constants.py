"""
Default constants for profitability calculator.

Contains default deposit levels configuration for ArbitroPLEX.
"""

from decimal import Decimal

from calculator.core.models import DepositLevel


# Default deposit levels for ArbitroPLEX
DEFAULT_LEVELS: list[DepositLevel] = [
    DepositLevel(
        level_number=1,
        min_amount=Decimal("1000"),
        roi_percent=Decimal("1.117"),
        roi_cap_percent=Decimal("500"),
        is_active=True,
        name="Starter",
    ),
    DepositLevel(
        level_number=2,
        min_amount=Decimal("5000"),
        roi_percent=Decimal("1.020"),
        roi_cap_percent=Decimal("500"),
        is_active=True,
        name="Standard",
    ),
    DepositLevel(
        level_number=3,
        min_amount=Decimal("10000"),
        roi_percent=Decimal("0.950"),
        roi_cap_percent=Decimal("500"),
        is_active=True,
        name="Professional",
    ),
    DepositLevel(
        level_number=4,
        min_amount=Decimal("50000"),
        roi_percent=Decimal("0.880"),
        roi_cap_percent=Decimal("500"),
        is_active=True,
        name="Premium",
    ),
    DepositLevel(
        level_number=5,
        min_amount=Decimal("100000"),
        roi_percent=Decimal("0.800"),
        roi_cap_percent=Decimal("500"),
        is_active=True,
        name="Elite",
    ),
]


def get_level_by_number(level_number: int) -> DepositLevel | None:
    """
    Get default level by number.

    Args:
        level_number: Level number (1-5)

    Returns:
        DepositLevel or None if not found

    Example:
        >>> level = get_level_by_number(1)
        >>> level.min_amount
        Decimal('1000')
    """
    for level in DEFAULT_LEVELS:
        if level.level_number == level_number:
            return level
    return None


def get_level_for_amount(amount: Decimal) -> DepositLevel | None:
    """
    Get highest available level for deposit amount.

    Args:
        amount: Deposit amount

    Returns:
        Highest level where amount >= min_amount, or None

    Example:
        >>> level = get_level_for_amount(Decimal("7500"))
        >>> level.level_number
        2
    """
    matching = [
        level for level in DEFAULT_LEVELS
        if level.is_active and amount >= level.min_amount
    ]
    if not matching:
        return None
    return max(matching, key=lambda lvl: lvl.level_number)


def get_active_levels() -> list[DepositLevel]:
    """
    Get all active deposit levels.

    Returns:
        List of active DepositLevel objects
    """
    return [level for level in DEFAULT_LEVELS if level.is_active]
