"""
Admin ROI Corridor Handler Module.

Manages ROI corridor configuration for deposit levels.
Supports two modes:
- Custom: Random rate from corridor (weighted to lower values)
- Equal: Fixed rate for all users

Allows setting for current or next session.

Module Structure:
- menu.py: Main menu and navigation
- level_config.py: Level ROI configuration display
- amount_setup.py: Level amount management
- corridor_setup.py: Corridor setup flow (mode & scope selection)
- corridor_input.py: Input handlers (min, max, fixed, reason)
- corridor_confirmation.py: Confirmation and saving
- history.py: History viewing
- period_setup.py: Period setup
- utils.py: Utility functions and notifications

This module refactors the original large roi_corridor.py file (1321 lines)
into smaller, well-organized modules while maintaining full backward compatibility.
"""

from __future__ import annotations

from aiogram import Router


# Create the main router for this module
router = Router(name="admin_roi_corridor")

# Import all handler registration functions
from bot.handlers.admin.roi_corridor.amount_setup import (
    register_amount_setup_handlers,
)
from bot.handlers.admin.roi_corridor.corridor_confirmation import (
    register_corridor_confirmation_handlers,
)
from bot.handlers.admin.roi_corridor.corridor_input import (
    register_corridor_input_handlers,
)
from bot.handlers.admin.roi_corridor.corridor_setup import (
    register_corridor_setup_handlers,
)
from bot.handlers.admin.roi_corridor.history import register_history_handlers
from bot.handlers.admin.roi_corridor.level_config import (
    register_level_config_handlers,
)
from bot.handlers.admin.roi_corridor.menu import register_menu_handlers
from bot.handlers.admin.roi_corridor.period_setup import (
    register_period_setup_handlers,
)


# Register all handlers to the router
register_menu_handlers(router)
register_level_config_handlers(router)
register_amount_setup_handlers(router)
register_corridor_setup_handlers(router)
register_corridor_input_handlers(router)
register_corridor_confirmation_handlers(router)
register_history_handlers(router)
register_period_setup_handlers(router)

# Re-export public functions for backward compatibility
# These imports ensure that existing code using these functions continues to work
from bot.handlers.admin.roi_corridor.amount_setup import (
    process_amount_confirmation,
    process_amount_input,
    process_level_amount_selection,
    start_amount_setup,
)
from bot.handlers.admin.roi_corridor.corridor_confirmation import (
    process_confirmation,
    show_confirmation,
)
from bot.handlers.admin.roi_corridor.corridor_input import (
    process_fixed_input,
    process_max_input,
    process_min_input,
    process_reason_input,
)
from bot.handlers.admin.roi_corridor.corridor_setup import (
    process_applies_to,
    process_level_selection,
    process_mode_selection,
    start_corridor_setup,
)
from bot.handlers.admin.roi_corridor.history import (
    show_level_history,
    start_history_view,
)
from bot.handlers.admin.roi_corridor.level_config import (
    show_current_settings,
    show_level_roi_config,  # IMPORTANT: Imported by deposit_management.py
)
from bot.handlers.admin.roi_corridor.menu import (
    back_to_deposit_management,
    show_roi_corridor_menu,
)
from bot.handlers.admin.roi_corridor.period_setup import (
    process_period_confirmation,
    process_period_input,
    start_period_setup,
)
from bot.handlers.admin.roi_corridor.utils import (
    check_cancel_or_back,
    notify_other_admins,
    notify_other_admins_period,
)


# Define __all__ to control what gets exported with "from ... import *"
__all__ = [
    # Router
    "router",
    # Menu functions
    "show_roi_corridor_menu",
    "back_to_deposit_management",
    # Level config functions (IMPORTANT: show_level_roi_config is used by deposit_management.py)
    "show_level_roi_config",
    "show_current_settings",
    # Amount setup functions
    "start_amount_setup",
    "process_level_amount_selection",
    "process_amount_input",
    "process_amount_confirmation",
    # Corridor setup functions
    "start_corridor_setup",
    "process_level_selection",
    "process_mode_selection",
    "process_applies_to",
    # Corridor input functions
    "process_reason_input",
    "process_min_input",
    "process_max_input",
    "process_fixed_input",
    # Corridor confirmation functions
    "show_confirmation",
    "process_confirmation",
    # History functions
    "start_history_view",
    "show_level_history",
    # Period setup functions
    "start_period_setup",
    "process_period_input",
    "process_period_confirmation",
    # Utility functions
    "check_cancel_or_back",
    "notify_other_admins",
    "notify_other_admins_period",
]
