"""
Default constants for profitability calculator.

Contains default deposit levels configuration for ArbitroPLEX.
Импортировано из единого источника истины: app.config.deposit_levels
"""

from decimal import Decimal

from calculator.core.models import DepositLevel

# Импортируем из единого источника истины
try:
    # Пытаемся импортировать из app.config.deposit_levels
    from app.config.deposit_levels import DEPOSIT_LEVELS, DepositLevelType

    # Создаем DEFAULT_LEVELS из единого источника истины
    # Исключаем тестовый уровень (level_number=0) для калькулятора
    DEFAULT_LEVELS: list[DepositLevel] = [
        DepositLevel(
            level_number=config.level_number,
            min_amount=config.min_amount,
            roi_percent=config.roi_percent,
            roi_cap_percent=Decimal(str(config.roi_cap_percent)),
            is_active=True,
            name=config.display_name,
        )
        for level_type, config in DEPOSIT_LEVELS.items()
        if config.level_number > 0  # Только уровни 1-5, без test
    ]

except ImportError:
    # Fallback на старые значения, если импорт не удался
    # (для обратной совместимости со старыми версиями)
    DEFAULT_LEVELS: list[DepositLevel] = [
        DepositLevel(
            level_number=1,
            min_amount=Decimal("100"),
            roi_percent=Decimal("2.0"),
            roi_cap_percent=Decimal("500"),
            is_active=True,
            name="Уровень 1",
        ),
        DepositLevel(
            level_number=2,
            min_amount=Decimal("700"),
            roi_percent=Decimal("2.0"),
            roi_cap_percent=Decimal("500"),
            is_active=True,
            name="Уровень 2",
        ),
        DepositLevel(
            level_number=3,
            min_amount=Decimal("1400"),
            roi_percent=Decimal("2.0"),
            roi_cap_percent=Decimal("500"),
            is_active=True,
            name="Уровень 3",
        ),
        DepositLevel(
            level_number=4,
            min_amount=Decimal("2500"),
            roi_percent=Decimal("2.0"),
            roi_cap_percent=Decimal("500"),
            is_active=True,
            name="Уровень 4",
        ),
        DepositLevel(
            level_number=5,
            min_amount=Decimal("4000"),
            roi_percent=Decimal("2.0"),
            roi_cap_percent=Decimal("500"),
            is_active=True,
            name="Уровень 5",
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
