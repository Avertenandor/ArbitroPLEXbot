"""
User service module.

Provides user management functionality including registration, authentication,
statistics, and wallet management.

Structure:
- core.py: Core user retrieval and profile management
- registration.py: User registration with referral support
- authentication.py: Financial password verification with rate limiting
- statistics.py: User statistics and balance calculations
- wallet.py: Wallet management with verification

Usage:
    from app.services.user import UserService

    user_service = UserService(session)
    user = await user_service.register_user(telegram_id, wallet, password)
    is_valid, error = await user_service.verify_financial_password(user_id, password)
    balance = await user_service.get_user_balance(user_id)
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user.authentication import UserAuthenticationMixin
from app.services.user.core import UserServiceCore
from app.services.user.registration import UserRegistrationMixin
from app.services.user.statistics import UserStatisticsMixin
from app.services.user.wallet import UserWalletMixin


class UserService(
    UserServiceCore,
    UserRegistrationMixin,
    UserAuthenticationMixin,
    UserStatisticsMixin,
    UserWalletMixin,
):
    """
    Combined user service.

    Inherits from all user service mixins to provide complete functionality.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize user service with all mixins.

        Args:
            session: Database session
        """
        # Initialize all parent classes
        UserServiceCore.__init__(self, session)
        UserRegistrationMixin.__init__(self, session)
        UserAuthenticationMixin.__init__(self, session)
        UserStatisticsMixin.__init__(self, session)
        UserWalletMixin.__init__(self, session)

        # Import ReferralService for registration
        from app.services.referral_service import ReferralService
        self.referral_service = ReferralService(session)


# Export for backward compatibility
__all__ = ["UserService"]
