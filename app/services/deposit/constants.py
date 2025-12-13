"""
Deposit levels configuration and constants.

Defines deposit level types, amounts, and helper functions.
Single source of truth: app.config.deposit_levels
"""

from decimal import Decimal
from typing import NamedTuple

# Импортируем из единого источника истины
from app.config.deposit_levels import (
    DEPOSIT_LEVELS as SOURCE_DEPOSIT_LEVELS,
    DepositLevelType,
    db_level_to_level_type as _db_level_to_level_type,
    get_level_config as _get_level_config,
    get_level_config_by_number as _get_level_config_by_number,
    get_next_level_type as _get_next_level_type,
    get_previous_level_type as _get_previous_level_type,
    level_type_to_db_level as _level_type_to_db_level,
)


# Deposit level type constants (для обратной совместимости)
LEVEL_TYPE_TEST = DepositLevelType.TEST.value
LEVEL_TYPE_LEVEL_1 = DepositLevelType.LEVEL_1.value
LEVEL_TYPE_LEVEL_2 = DepositLevelType.LEVEL_2.value
LEVEL_TYPE_LEVEL_3 = DepositLevelType.LEVEL_3.value
LEVEL_TYPE_LEVEL_4 = DepositLevelType.LEVEL_4.value
LEVEL_TYPE_LEVEL_5 = DepositLevelType.LEVEL_5.value

# All valid level types in order
LEVEL_TYPES = [
    LEVEL_TYPE_TEST,
    LEVEL_TYPE_LEVEL_1,
    LEVEL_TYPE_LEVEL_2,
    LEVEL_TYPE_LEVEL_3,
    LEVEL_TYPE_LEVEL_4,
    LEVEL_TYPE_LEVEL_5,
]


class DepositLevelConfig(NamedTuple):
    """Configuration for a deposit level."""

    level_type: str
    db_level: int  # Database level (0 for test, 1-5 for levels)
    min_amount: Decimal
    max_amount: Decimal
    display_name: str


# Build DEPOSIT_LEVEL_CONFIGS from single source of truth
DEPOSIT_LEVEL_CONFIGS = {
    config.level_type.value: DepositLevelConfig(
        level_type=config.level_type.value,
        db_level=config.level_number,
        min_amount=config.min_amount,
        max_amount=config.max_amount,
        display_name=config.display_name,
    )
    for config in SOURCE_DEPOSIT_LEVELS.values()
}

# Legacy DEPOSIT_LEVELS for backward compatibility (maps db_level -> min_amount)
DEPOSIT_LEVELS = {
    config.level_number: config.min_amount
    for config in SOURCE_DEPOSIT_LEVELS.values()
}

# Partner requirements (DISABLED - no partners required)
PARTNER_REQUIREMENTS = {
    1: 0,
    2: 0,
    3: 0,
    4: 0,
    5: 0,
}


def get_level_config(level_type: str) -> DepositLevelConfig | None:
    """
    Get level configuration by level type.

    Args:
        level_type: Level type (e.g., "test", "level_1")

    Returns:
        DepositLevelConfig or None if not found
    """
    return DEPOSIT_LEVEL_CONFIGS.get(level_type)


def get_level_config_by_db_level(db_level: int) -> DepositLevelConfig | None:
    """
    Get level configuration by database level number.

    Args:
        db_level: Database level (0 for test, 1-5 for levels)

    Returns:
        DepositLevelConfig or None if not found
    """
    for config in DEPOSIT_LEVEL_CONFIGS.values():
        if config.db_level == db_level:
            return config
    return None


def level_type_to_db_level(level_type: str) -> int | None:
    """
    Convert level type to database level number.

    Args:
        level_type: Level type (e.g., "test", "level_1")

    Returns:
        Database level number or None if not found
    """
    # Используем функцию из единого источника истины
    return _level_type_to_db_level(level_type)


def db_level_to_level_type(db_level: int) -> str | None:
    """
    Convert database level number to level type.

    Args:
        db_level: Database level (0 for test, 1-5 for levels)

    Returns:
        Level type or None if not found
    """
    # Используем функцию из единого источника истины
    level_type = _db_level_to_level_type(db_level)
    return level_type.value if level_type else None


def get_next_level_type(current_level_type: str) -> str | None:
    """
    Get the next level type in sequence.

    Args:
        current_level_type: Current level type

    Returns:
        Next level type or None if at max level
    """
    # Используем функцию из единого источника истины
    level_type = _get_next_level_type(current_level_type)
    return level_type.value if level_type else None


def get_previous_level_type(current_level_type: str) -> str | None:
    """
    Get the previous level type in sequence.

    Args:
        current_level_type: Current level type

    Returns:
        Previous level type or None if at first level
    """
    # Используем функцию из единого источника истины
    level_type = _get_previous_level_type(current_level_type)
    return level_type.value if level_type else None
