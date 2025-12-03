"""Admin utilities package."""

from .admin_checks import (
    ROLE_DISPLAY,
    check_admin_access,
    format_role_display,
    get_admin_or_deny,
    is_last_super_admin,
)

__all__ = [
    "check_admin_access",
    "get_admin_or_deny",
    "is_last_super_admin",
    "format_role_display",
    "ROLE_DISPLAY",
]
