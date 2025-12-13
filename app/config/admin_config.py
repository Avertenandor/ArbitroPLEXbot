"""
Admin Configuration.

Provides admin verification data with support for environment variable overrides.
Admins are identified ONLY by telegram_id for security.
"""

import os
from typing import Any

from loguru import logger


def _parse_admin_ids_from_env() -> dict[int, dict[str, Any]]:
    """
    Parse admin IDs from environment variables.

    Expected format:
    VERIFIED_ADMIN_IDS=1040687384:VladarevInvestBrok:super_admin:Командир,1691026253:AI_XAN:extended_admin:Саша (Tech Deputy)

    Format: telegram_id:username:role:name,telegram_id:username:role:name,...

    Returns:
        dict[int, dict[str, Any]]: Parsed admin configuration
    """
    env_value = os.getenv("VERIFIED_ADMIN_IDS", "")
    if not env_value:
        return {}

    admins = {}
    for entry in env_value.split(","):
        entry = entry.strip()
        if not entry:
            continue

        parts = entry.split(":")
        if len(parts) != 4:
            logger.warning(
                f"Invalid VERIFIED_ADMIN_IDS entry: {entry}. "
                f"Expected format: telegram_id:username:role:name"
            )
            continue

        try:
            telegram_id = int(parts[0].strip())
            username = parts[1].strip()
            role = parts[2].strip()
            name = parts[3].strip()

            admins[telegram_id] = {
                "username": username,
                "role": role,
                "name": name,
            }
        except ValueError as e:
            logger.warning(
                f"Failed to parse VERIFIED_ADMIN_IDS entry: {entry}. Error: {e}"
            )
            continue

    return admins


# Default admin configuration (fallback if not set in environment)
_DEFAULT_VERIFIED_ADMIN_IDS = {
    1040687384: {
        "username": "VladarevInvestBrok",
        "role": "super_admin",
        "name": "Командир"
    },
    1691026253: {
        "username": "AI_XAN",
        "role": "extended_admin",
        "name": "Саша (Tech Deputy)"
    },
    241568583: {
        "username": "natder",
        "role": "extended_admin",
        "name": "Наташа"
    },
    6540613027: {
        "username": "ded_vtapkax",
        "role": "extended_admin",
        "name": "Влад"
    },
}


def get_verified_admin_ids() -> dict[int, dict[str, Any]]:
    """
    Get verified admin IDs from environment or defaults.

    Priority:
    1. VERIFIED_ADMIN_IDS environment variable
    2. Default hardcoded values

    Returns:
        dict[int, dict[str, Any]]: Admin configuration mapping telegram_id to admin info
    """
    # Try to load from environment
    env_admins = _parse_admin_ids_from_env()

    if env_admins:
        logger.info(
            f"Loaded {len(env_admins)} verified admins from VERIFIED_ADMIN_IDS environment variable"
        )
        return env_admins

    # Fallback to defaults
    logger.info(
        f"Using default verified admin configuration ({len(_DEFAULT_VERIFIED_ADMIN_IDS)} admins)"
    )
    return _DEFAULT_VERIFIED_ADMIN_IDS


# Global instance - loaded once at startup
VERIFIED_ADMIN_IDS = get_verified_admin_ids()
