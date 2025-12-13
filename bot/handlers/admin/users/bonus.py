"""
Admin User Bonus Management Handler.

Handles admin-initiated bonus credit operations:
- Grant bonus to user
- View user's bonuses
- Cancel active bonus

This module serves as the main entry point and coordinates
bonus_grant and bonus_view submodules.
"""

from aiogram import Router
from aiogram.fsm.state import State, StatesGroup


router = Router(name="admin_users_bonus")


class UserBonusStates(StatesGroup):
    """States for user profile bonus management flow.

    Note: Named UserBonusStates to avoid conflict with
    bot.handlers.admin.bonus_v2.states.BonusStates which handles
    the main bonus management menu workflow.
    """

    waiting_amount = State()
    waiting_reason = State()
    # Cancel bonus flow states
    cancel_select_bonus = State()  # Step 1: Select bonus ID
    cancel_select_reason = State()  # Step 2: Select/enter reason
    cancel_confirm = State()  # Step 3: Confirm cancellation


# Import submodule routers
from bot.handlers.admin.users import (  # noqa: E402
    bonus_cancel,
    bonus_grant,
    bonus_view,
)

# Include submodule routers
router.include_router(bonus_grant.router)
router.include_router(bonus_view.router)
router.include_router(bonus_cancel.router)

# Register state-specific handlers
router.message.register(
    bonus_grant.process_bonus_amount,
    UserBonusStates.waiting_amount,
)
router.message.register(
    bonus_grant.process_bonus_reason,
    UserBonusStates.waiting_reason,
)
router.message.register(
    bonus_cancel.process_cancel_select_bonus,
    UserBonusStates.cancel_select_bonus,
)
router.message.register(
    bonus_cancel.process_cancel_select_reason,
    UserBonusStates.cancel_select_reason,
)
router.message.register(
    bonus_cancel.process_cancel_confirm,
    UserBonusStates.cancel_confirm,
)


__all__ = ["router", "UserBonusStates"]
