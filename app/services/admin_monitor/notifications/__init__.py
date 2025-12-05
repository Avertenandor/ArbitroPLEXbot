"""
Admin Event Monitor - Notifications Package.

This package contains specialized notification methods grouped by category:
- financial: Financial notifications (deposits, withdrawals, PLEX, referrals)
- security: Security alerts and blacklist notifications
- user: User-related notifications (registration, recovery)
- support: Support tickets, inquiries, and appeals
- system: System errors and maintenance notifications
"""

from .financial import (
    notify_deposit_error,
    notify_large_transaction,
    notify_new_deposit,
    notify_plex_payment,
    notify_referral_bonus,
    notify_unidentified_deposit,
    notify_withdrawal_completed,
    notify_withdrawal_request,
)
from .security import (
    notify_security_alert,
    notify_user_blacklisted,
)
from .support import (
    notify_appeal_created,
    notify_new_inquiry,
    notify_new_support_ticket,
)
from .system import (
    notify_maintenance_mode,
    notify_system_error,
)
from .user import (
    notify_finpass_recovery,
    notify_new_registration,
)

__all__ = [
    # Financial
    "notify_new_deposit",
    "notify_deposit_error",
    "notify_unidentified_deposit",
    "notify_withdrawal_request",
    "notify_withdrawal_completed",
    "notify_large_transaction",
    "notify_plex_payment",
    "notify_referral_bonus",
    # Security
    "notify_security_alert",
    "notify_user_blacklisted",
    # User
    "notify_new_registration",
    "notify_finpass_recovery",
    # Support
    "notify_new_support_ticket",
    "notify_new_inquiry",
    "notify_appeal_created",
    # System
    "notify_system_error",
    "notify_maintenance_mode",
]
