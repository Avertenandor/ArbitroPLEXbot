"""
Withdrawal eligibility checking module.

This module contains functions for checking if a user is eligible to withdraw funds,
including verification requirements based on deposit levels.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from bot.i18n.loader import get_text


async def is_level1_only_user(session: AsyncSession, user_id: int) -> bool:
    """
    Check if user has only level 1 deposits (10$ deposits).
    Level 1 users don't need phone/email verification.

    Returns:
        True if user has only level 1 deposits or no deposits
    """
    from app.repositories.deposit_repository import DepositRepository

    deposit_repo = DepositRepository(session)
    active_deposits = await deposit_repo.get_active_deposits(user_id)

    if not active_deposits:
        return True  # No deposits = level 1 eligible

    # Check if all deposits are level 1
    return all(d.level == 1 for d in active_deposits)


async def check_withdrawal_eligibility(
    session: AsyncSession,
    user: User,
    lang: str = "ru"
) -> tuple[bool, str | None]:
    """
    Check if user can withdraw:
    - ALL users need financial password (is_verified)
    - Level 2+ users also need phone OR email

    Returns:
        (can_withdraw, error_message)
    """
    # Everyone needs financial password
    if not user.is_verified:
        return False, get_text('withdrawal.finpass_required', lang=lang)

    # Check if level 2+ user needs additional verification
    is_level1 = await is_level1_only_user(session, user.id)

    if not is_level1:
        # Level 2+ needs phone OR email
        if not user.phone and not user.email:
            return False, get_text('withdrawal.verification_required', lang=lang)

    return True, None
