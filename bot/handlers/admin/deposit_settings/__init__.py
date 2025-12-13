"""
Deposit settings handler.

Allows admins to configure max open deposit level and manage level
availability. R17-2: Temporary level deactivation via is_active flag.
Enhanced with deposit corridors and PLEX rate management.

This module has been refactored into sub-modules for better organization:
- constants: Shared constants (emoji mappings)
- display: Display handlers (settings, statistics, status)
- management: Level management handlers (toggle, set max level)
- parameters: Parameter handlers (corridors, PLEX rates)
- navigation: Navigation handlers (back to admin panel)
"""

from aiogram import Router

from . import display, management, navigation, parameters


# Create main router and include all sub-routers
router = Router()
router.include_router(display.router)
router.include_router(management.router)
router.include_router(parameters.router)
router.include_router(navigation.router)

__all__ = ["router"]
