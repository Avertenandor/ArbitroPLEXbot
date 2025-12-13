"""
AI Tool Definitions.

Contains all tool definitions for AI assistant,
organized by category for better maintainability.

This module now re-exports tools from the tools package.
"""

from typing import Any

from app.services.ai.prompts import UserRole
from app.services.ai.tools import (
    get_admin_management_tools,
    get_appeals_tools,
    get_blacklist_tools,
    get_bonus_tools,
    get_deposits_tools,
    get_finpass_tools,
    get_inquiries_tools,
    get_interview_tools,
    get_logs_tools,
    get_messaging_tools,
    get_referral_tools,
    get_roi_tools,
    get_security_tools,
    get_settings_tools,
    get_statistics_tools,
    get_system_admin_tools,
    get_user_management_tools,
    get_user_wallet_tools,
    get_wallet_tools,
    get_withdrawals_tools,
)

__all__ = [
    "get_admin_management_tools",
    "get_all_admin_tools",
    "get_appeals_tools",
    "get_blacklist_tools",
    "get_bonus_tools",
    "get_deposits_tools",
    "get_finpass_tools",
    "get_inquiries_tools",
    "get_interview_tools",
    "get_logs_tools",
    "get_messaging_tools",
    "get_referral_tools",
    "get_roi_tools",
    "get_security_tools",
    "get_settings_tools",
    "get_statistics_tools",
    "get_system_admin_tools",
    "get_user_management_tools",
    "get_user_wallet_tools",
    "get_wallet_tools",
    "get_withdrawals_tools",
]


def get_all_admin_tools(
    role: UserRole = UserRole.ADMIN,
) -> list[dict[str, Any]]:
    """
    Get all admin tools based on role.

    Args:
        role: User role

    Returns:
        List of all available tools for the role
    """
    tools = []

    # Basic admin tools
    tools.extend(get_messaging_tools(role))
    tools.extend(get_bonus_tools())
    tools.extend(get_appeals_tools())
    tools.extend(get_inquiries_tools())
    tools.extend(get_user_management_tools())
    tools.extend(get_statistics_tools())
    tools.extend(get_withdrawals_tools())
    tools.extend(get_deposits_tools())
    tools.extend(get_roi_tools())
    tools.extend(get_blacklist_tools())
    tools.extend(get_finpass_tools())
    tools.extend(get_wallet_tools())
    tools.extend(get_referral_tools())
    tools.extend(get_logs_tools())
    tools.extend(get_settings_tools())
    tools.extend(get_security_tools())

    # Super admin only tools
    if role == UserRole.SUPER_ADMIN:
        tools.extend(get_interview_tools())
        tools.extend(get_system_admin_tools())
        tools.extend(get_admin_management_tools())

    return tools
