"""
Admin Event Monitor - Main Package.

This package provides a centralized service for monitoring and notifying
administrators about events in the bot.

Module Structure:
- constants.py: Event categories, priorities, emojis, and Russian names
- formatter.py: Message formatting utilities
- monitor.py: Core monitoring class with basic notify() method
- extended_monitor.py: Extended monitor with specialized notification methods
- notifications/: Package with specialized notification methods grouped by category
  - financial.py: Deposits, withdrawals, PLEX, referrals
  - security.py: Security alerts and blacklist
  - user.py: Registration, verification, recovery
  - support.py: Tickets, inquiries, appeals
  - system.py: Errors and maintenance

Public API:
- AdminEventMonitor: Main class with all notification methods
- EventCategory: Enum for event categories
- EventPriority: Enum for event priorities
- get_admin_monitor(): Factory function to create monitor instance
"""

# Export constants
from .constants import (
    CATEGORY_EMOJI,
    CATEGORY_NAMES_RU,
    PRIORITY_EMOJI,
    PRIORITY_NAMES_RU,
    EventCategory,
    EventPriority,
)

# Export the extended monitor (with all notification methods)
from .extended_monitor import AdminEventMonitor, get_admin_monitor

# Export formatter for advanced usage
from .formatter import format_admin_message

__all__ = [
    # Main class and factory
    "AdminEventMonitor",
    "get_admin_monitor",
    # Enums
    "EventCategory",
    "EventPriority",
    # Constants (for advanced usage)
    "CATEGORY_EMOJI",
    "CATEGORY_NAMES_RU",
    "PRIORITY_EMOJI",
    "PRIORITY_NAMES_RU",
    # Formatter (for advanced usage)
    "format_admin_message",
]
