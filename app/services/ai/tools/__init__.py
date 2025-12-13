"""
AI Tools Package.

Contains all tool definitions for AI assistant,
organized by category for better maintainability.
"""

from app.services.ai.tools.admin_tools import (
    get_admin_management_tools,
    get_system_admin_tools,
)
from app.services.ai.tools.appeals_tools import get_appeals_tools
from app.services.ai.tools.blacklist_tools import get_blacklist_tools
from app.services.ai.tools.bonus_tools import get_bonus_tools
from app.services.ai.tools.deposits_tools import get_deposits_tools
from app.services.ai.tools.finpass_tools import get_finpass_tools
from app.services.ai.tools.inquiries_tools import get_inquiries_tools
from app.services.ai.tools.interview_tools import get_interview_tools
from app.services.ai.tools.logs_tools import get_logs_tools
from app.services.ai.tools.messaging_tools import get_messaging_tools
from app.services.ai.tools.referral_tools import get_referral_tools
from app.services.ai.tools.roi_tools import get_roi_tools
from app.services.ai.tools.security_tools import get_security_tools
from app.services.ai.tools.settings_tools import get_settings_tools
from app.services.ai.tools.statistics_tools import get_statistics_tools
from app.services.ai.tools.user_tools import (
    get_user_management_tools,
    get_user_wallet_tools,
)
from app.services.ai.tools.wallet_tools import get_wallet_tools
from app.services.ai.tools.withdrawals_tools import get_withdrawals_tools

__all__ = [
    "get_admin_management_tools",
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
