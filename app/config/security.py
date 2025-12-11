"""
Security Configuration - Centralized security whitelist constants.

This module contains all security-related constants for the ArbitroPLEX platform,
including admin IDs, trusted admin lists, and technical deputies.
"""

# Super admin (owner) - Командир (Alexander Vladarev)
SUPER_ADMIN_IDS = [1040687384]

# Trusted admins with elevated privileges (balance changes, withdrawals, etc.)
# Format: [telegram_id, ...]
TRUSTED_ADMIN_IDS = [
    1040687384,  # Командир
    1691026253,  # @AI_XAN (Tech Deputy)
    241568583,  # Trusted admin
    6540613027,  # Trusted admin
]

# Technical deputies (usernames without @)
# These users have EXTENDED_ADMIN access level
TECH_DEPUTIES = ["AIXAN", "AI_XAN"]

# Tech deputy telegram ID for direct identification
TECH_DEPUTY_TELEGRAM_ID = 1691026253


def is_super_admin(telegram_id: int) -> bool:
    """Check if user is a super admin (owner)."""
    return telegram_id in SUPER_ADMIN_IDS


def is_trusted_admin(telegram_id: int) -> bool:
    """Check if user is a trusted admin with elevated privileges."""
    return telegram_id in TRUSTED_ADMIN_IDS


def is_tech_deputy(telegram_id: int | None = None, username: str | None = None) -> bool:
    """
    Check if user is a technical deputy.

    Priority: telegram_id > username
    """
    if telegram_id == TECH_DEPUTY_TELEGRAM_ID:
        return True
    if username and username.replace("@", "") in TECH_DEPUTIES:
        return True
    return False
