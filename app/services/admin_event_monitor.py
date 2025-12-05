"""
Admin Event Monitoring Service.

REFACTORED: This file has been refactored into smaller modules.
For backward compatibility, all public APIs are re-exported from here.

New module structure:
- app/services/admin_monitor/constants.py: Event enums and constants
- app/services/admin_monitor/formatter.py: Message formatting
- app/services/admin_monitor/monitor.py: Core monitoring class
- app/services/admin_monitor/extended_monitor.py: Extended with notification methods
- app/services/admin_monitor/notifications/: Specialized notification methods
  - financial.py: Deposits, withdrawals, PLEX, referrals
  - security.py: Security alerts and blacklist
  - user.py: Registration and recovery
  - support.py: Tickets, inquiries, appeals
  - system.py: Errors and maintenance

To use the new structure directly:
    from app.services.admin_monitor import AdminEventMonitor, EventCategory, EventPriority

This provides the same API as before, but the implementation is now
better organized into smaller, focused modules.
"""

# Re-export everything from the new admin_monitor package
from app.services.admin_monitor import (
    CATEGORY_EMOJI,
    CATEGORY_NAMES_RU,
    PRIORITY_EMOJI,
    PRIORITY_NAMES_RU,
    AdminEventMonitor,
    EventCategory,
    EventPriority,
    format_admin_message,
    get_admin_monitor,
)

__all__ = [
    # Main class and factory
    "AdminEventMonitor",
    "get_admin_monitor",
    # Enums
    "EventCategory",
    "EventPriority",
    # Constants
    "CATEGORY_EMOJI",
    "CATEGORY_NAMES_RU",
    "PRIORITY_EMOJI",
    "PRIORITY_NAMES_RU",
    # Formatter
    "format_admin_message",
]
