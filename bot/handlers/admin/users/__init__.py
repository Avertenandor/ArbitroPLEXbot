"""
Admin Users Handler - Refactored Module Structure

This module has been refactored from a single 1068-line file into smaller,
well-organized modules for better maintainability.

Module Structure:
- menu.py: Main users management menu and navigation
- search.py: User search by username, telegram ID, wallet address
- list.py: Paginated user list display and selection
- profile.py: Detailed user profile display
- balance.py: User balance adjustments (credit/debit)
- security.py: Block/unblock/terminate user accounts
- transactions.py: Transaction history display
- deposits.py: Admin-initiated blockchain deposit scanning
- referrals.py: Referral statistics display

Backward Compatibility:
The original users.py exported a single router object. This __init__.py
aggregates all sub-module routers into a single router to maintain
backward compatibility with existing imports:
    from bot.handlers.admin import users
    users.router  # Works as before
"""

from aiogram import Router

# Import all sub-module routers
from bot.handlers.admin.users import (
    balance,
    bonus,
    deposits,
    list,
    menu,
    profile,
    referrals,
    search,
    security,
    transactions,
)

# Create a main router that includes all sub-routers
router = Router(name="admin_users")

# Include all sub-routers in the correct order
# Order matters: more specific handlers should be registered before generic ones

# 1. Menu and navigation (base functionality)
router.include_router(menu.router)

# 2. Search functionality
router.include_router(search.router)

# 3. List management
router.include_router(list.router)

# 4. Profile display (must be before security for proper handler ordering)
router.include_router(profile.router)

# 5. Balance management
router.include_router(balance.router)

# 6. Security (block/terminate) - must be after profile to allow profile handlers priority
router.include_router(security.router)

# 7. Transaction history
router.include_router(transactions.router)

# 8. Deposit scanning
router.include_router(deposits.router)

# 9. Referral statistics
router.include_router(referrals.router)

# 10. Bonus management
router.include_router(bonus.router)

# Export the main router for backward compatibility
__all__ = ["router"]
