"""
Bot constants module.

Contains rules, levels, and other constant values.
"""

from bot.constants.rules import (
    LEVELS,
    LEVELS_TABLE,
    RULES_FULL_TEXT,
    RULES_SHORT_TEXT,
    get_max_deposits_for_plex_balance,
    get_required_plex_for_deposits,
    get_user_level,
)

__all__ = [
    "LEVELS",
    "LEVELS_TABLE",
    "RULES_FULL_TEXT",
    "RULES_SHORT_TEXT",
    "get_max_deposits_for_plex_balance",
    "get_required_plex_for_deposits",
    "get_user_level",
]
