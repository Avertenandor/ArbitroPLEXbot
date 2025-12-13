"""
Referral Module - REPLY KEYBOARDS ONLY!

This module has been refactored into smaller, well-organized sub-modules for better
maintainability. Each sub-module handles a specific aspect of referral functionality.

Module structure:
- list.py: Referral list viewing and navigation (4 handlers)
  * _show_referral_list - Helper to show paginated referral lists
  * handle_my_referrals - View all referrals
  * handle_referral_level_selection - Select referral level
  * handle_referral_pagination - Navigate pages

- stats.py: Statistics and earnings display (3 handlers)
  * handle_my_earnings - View earnings breakdown
  * handle_referral_stats - Comprehensive statistics with link sharing
  * handle_referral_analytics - Detailed analytics with charts

- link.py: Link sharing and copying (2 handlers)
  * handle_copy_ref_link - Copy link via inline button
  * handle_copy_link_button - Copy link via reply button

- structure.py: User chain and structure visualization (2 handlers)
  * handle_who_invited_me - View referrer chain
  * handle_my_structure - View referral tree structure

- leaderboard.py: Top partners ranking (1 handler)
  * handle_top_partners - View leaderboard

- promo.py: Promo materials (1 handler)
  * handle_promo_materials - View promo texts and QR code

All handlers are registered to a single main router that is exported for use in bot/main.py.
This maintains backward compatibility - you can still import this module and access router.
"""

from aiogram import Router

# Import all sub-module routers
from . import leaderboard, link, list, promo, stats, structure


# Create main router for referral functionality
router = Router(name="referral")

# Include all sub-routers in the main router
# Order matters: more specific patterns should come first
router.include_router(list.router)
router.include_router(stats.router)
router.include_router(link.router)
router.include_router(structure.router)
router.include_router(leaderboard.router)
router.include_router(promo.router)

# Export router for backward compatibility
# This allows bot/main.py to continue using:
# from bot.handlers import referral; dp.include_router(referral.router)
__all__ = ["router"]
