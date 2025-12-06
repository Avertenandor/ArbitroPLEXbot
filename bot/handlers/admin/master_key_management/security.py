"""
Security utilities for master key management.

Contains:
- Super admin ID configuration
- Access control functions
"""

import os


# Get SUPER_ADMIN_TELEGRAM_ID from environment variable
SUPER_ADMIN_TELEGRAM_ID = int(os.getenv("SUPER_ADMIN_TELEGRAM_ID", "0"))

# Validate at module load time
if not SUPER_ADMIN_TELEGRAM_ID:
    raise ValueError(
        "SUPER_ADMIN_TELEGRAM_ID environment variable is required. "
        "Set it in your .env file with your Telegram user ID."
    )


def is_super_admin(telegram_id: int | None) -> bool:
    """
    Check if user is the super admin.

    Args:
        telegram_id: Telegram user ID

    Returns:
        True if user is super admin
    """
    return telegram_id == SUPER_ADMIN_TELEGRAM_ID
