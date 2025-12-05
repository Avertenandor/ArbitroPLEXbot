"""
User wallet management functionality.

Handles wallet address changes with verification and history tracking.
"""

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository


class UserWalletMixin:
    """
    Mixin for user wallet management functionality.

    Provides methods for changing wallet addresses with verification.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize user wallet mixin."""
        self.session = session
        self.user_repo = UserRepository(session)

    async def change_wallet(
        self, user_id: int, new_wallet_address: str, financial_password: str
    ) -> tuple[bool, str]:
        """
        Change user wallet address with financial password verification.

        Args:
            user_id: User ID
            new_wallet_address: New wallet address
            financial_password: Financial password for verification

        Returns:
            Tuple (success, error_message)
        """
        # 1. Verify financial password with rate limiting
        # This will be called from the combined UserService which has the method
        is_valid, error_msg = await self.verify_financial_password(user_id, financial_password)
        if not is_valid:
            return False, error_msg or "Неверный финансовый пароль"

        # 2. Check uniqueness
        existing = await self.user_repo.get_by_wallet_address(new_wallet_address)
        if existing and existing.id != user_id:
            return False, "Wallet address is already used by another user"

        # 3. Get user
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return False, "User not found"

        old_wallet = user.wallet_address

        # 4. Create history record
        from app.models.user_wallet_history import UserWalletHistory

        history = UserWalletHistory(
            user_id=user_id,
            old_wallet_address=old_wallet,
            new_wallet_address=new_wallet_address,
        )
        self.session.add(history)

        # 5. Update user
        user.wallet_address = new_wallet_address
        self.session.add(user)

        try:
            await self.session.commit()
            logger.info(
                f"User {user_id} changed wallet from {old_wallet} to {new_wallet_address}"
            )
            return True, ""
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to change wallet for user {user_id}: {e}")
            return False, f"Database error: {e}"
