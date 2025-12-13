"""
Deposit levels configuration and constants.

Defines deposit level types, amounts, and helper functions.
Single source of truth: app.config.business_constants.DEPOSIT_LEVELS
"""

from decimal import Decimal
from typing import NamedTuple

from app.config.business_constants import DEPOSIT_LEVELS as BUSINESS_DEPOSIT_LEVELS


# Deposit level type constants
LEVEL_TYPE_TEST = "test"
LEVEL_TYPE_LEVEL_1 = "level_1"
LEVEL_TYPE_LEVEL_2 = "level_2"
LEVEL_TYPE_LEVEL_3 = "level_3"
LEVEL_TYPE_LEVEL_4 = "level_4"
LEVEL_TYPE_LEVEL_5 = "level_5"

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


# Build DEPOSIT_LEVEL_CONFIGS from business constants (single source of truth)
DEPOSIT_LEVEL_CONFIGS = {
    LEVEL_TYPE_TEST: DepositLevelConfig(
        level_type=LEVEL_TYPE_TEST,
        db_level=0,
        min_amount=Decimal(str(BUSINESS_DEPOSIT_LEVELS["test"]["min"])),
        max_amount=Decimal(str(BUSINESS_DEPOSIT_LEVELS["test"]["max"])),
        display_name=BUSINESS_DEPOSIT_LEVELS["test"]["name"],
    ),
    LEVEL_TYPE_LEVEL_1: DepositLevelConfig(
        level_type=LEVEL_TYPE_LEVEL_1,
        db_level=1,
        min_amount=Decimal(str(BUSINESS_DEPOSIT_LEVELS["level_1"]["min"])),
        max_amount=Decimal(str(BUSINESS_DEPOSIT_LEVELS["level_1"]["max"])),
        display_name=BUSINESS_DEPOSIT_LEVELS["level_1"]["name"],
    ),
    LEVEL_TYPE_LEVEL_2: DepositLevelConfig(
        level_type=LEVEL_TYPE_LEVEL_2,
        db_level=2,
        min_amount=Decimal(str(BUSINESS_DEPOSIT_LEVELS["level_2"]["min"])),
        max_amount=Decimal(str(BUSINESS_DEPOSIT_LEVELS["level_2"]["max"])),
        display_name=BUSINESS_DEPOSIT_LEVELS["level_2"]["name"],
    ),
    LEVEL_TYPE_LEVEL_3: DepositLevelConfig(
        level_type=LEVEL_TYPE_LEVEL_3,
        db_level=3,
        min_amount=Decimal(str(BUSINESS_DEPOSIT_LEVELS["level_3"]["min"])),
        max_amount=Decimal(str(BUSINESS_DEPOSIT_LEVELS["level_3"]["max"])),
        display_name=BUSINESS_DEPOSIT_LEVELS["level_3"]["name"],
    ),
    LEVEL_TYPE_LEVEL_4: DepositLevelConfig(
        level_type=LEVEL_TYPE_LEVEL_4,
        db_level=4,
        min_amount=Decimal(str(BUSINESS_DEPOSIT_LEVELS["level_4"]["min"])),
        max_amount=Decimal(str(BUSINESS_DEPOSIT_LEVELS["level_4"]["max"])),
        display_name=BUSINESS_DEPOSIT_LEVELS["level_4"]["name"],
    ),
    LEVEL_TYPE_LEVEL_5: DepositLevelConfig(
        level_type=LEVEL_TYPE_LEVEL_5,
        db_level=5,
        min_amount=Decimal(str(BUSINESS_DEPOSIT_LEVELS["level_5"]["min"])),
        max_amount=Decimal(str(BUSINESS_DEPOSIT_LEVELS["level_5"]["max"])),
        display_name=BUSINESS_DEPOSIT_LEVELS["level_5"]["name"],
    ),
}

# Legacy DEPOSIT_LEVELS for backward compatibility (maps db_level -> min_amount)
DEPOSIT_LEVELS = {
    0: Decimal(str(BUSINESS_DEPOSIT_LEVELS["test"]["min"])),
    1: Decimal(str(BUSINESS_DEPOSIT_LEVELS["level_1"]["min"])),
    2: Decimal(str(BUSINESS_DEPOSIT_LEVELS["level_2"]["min"])),
    3: Decimal(str(BUSINESS_DEPOSIT_LEVELS["level_3"]["min"])),
    4: Decimal(str(BUSINESS_DEPOSIT_LEVELS["level_4"]["min"])),
    5: Decimal(str(BUSINESS_DEPOSIT_LEVELS["level_5"]["min"])),
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
    config = get_level_config(level_type)
    return config.db_level if config else None


def db_level_to_level_type(db_level: int) -> str | None:
    """
    Convert database level number to level type.

    Args:
        db_level: Database level (0 for test, 1-5 for levels)

    Returns:
        Level type or None if not found
    """
    config = get_level_config_by_db_level(db_level)
    return config.level_type if config else None


def get_next_level_type(current_level_type: str) -> str | None:
    """
    Get the next level type in sequence.

    Args:
        current_level_type: Current level type

    Returns:
        Next level type or None if at max level
    """
    try:
        current_index = LEVEL_TYPES.index(current_level_type)
        if current_index < len(LEVEL_TYPES) - 1:
            return LEVEL_TYPES[current_index + 1]
    except ValueError:
        pass
    return None


def get_previous_level_type(current_level_type: str) -> str | None:
    """
    Get the previous level type in sequence.

    Args:
        current_level_type: Current level type

    Returns:
        Previous level type or None if at first level
    """
    try:
        current_index = LEVEL_TYPES.index(current_level_type)
        if current_index > 0:
            return LEVEL_TYPES[current_index - 1]
    except ValueError:
        pass
    return None
