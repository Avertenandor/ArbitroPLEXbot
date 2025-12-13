import json
import os
from typing import Any

from loguru import logger


def _parse_admin_ids_from_env() -> dict[int, dict[str, Any]]:
    env_value = os.getenv("VERIFIED_ADMIN_IDS", "")
    if not env_value:
        return {}

    try:
        data = json.loads(env_value)
        admins = {}
        for telegram_id_str, admin_data in data.items():
            try:
                telegram_id = int(telegram_id_str)
                admins[telegram_id] = admin_data
            except ValueError as e:
                logger.warning(
                    f"Invalid telegram_id in VERIFIED_ADMIN_IDS: {telegram_id_str}. Error: {e}"
                )
                continue
        return admins
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse VERIFIED_ADMIN_IDS as JSON: {e}")
        return {}


# Default to empty dict - all admin IDs should be loaded from env
_DEFAULT_VERIFIED_ADMIN_IDS = {}


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
