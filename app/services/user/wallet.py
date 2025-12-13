"""
User wallet management functionality.

Handles wallet address changes with verification and history tracking.
"""

from loguru import logger
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from redis.asyncio import Redis
except ImportError:
    import redis.asyncio as redis
    Redis = redis.Redis

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
        self,
        user_id: int,
        new_wallet_address: str,
        financial_password: str,
        redis_client: Redis | None = None,
    ) -> tuple[bool, str]:
        """
        Change user wallet address with financial password verification.

        Args:
            user_id: User ID
            new_wallet_address: New wallet address
            financial_password: Financial password for verification
            redis_client: Optional Redis client for cache invalidation

        Returns:
            Tuple (success, error_message)
        """
        # 1. Verify financial password with rate limiting
        # This will be called from the combined UserService which has the method
        is_valid, error_msg = await self.verify_financial_password(user_id, financial_password)
        if not is_valid:
            return False, error_msg or "Неверный финансовый пароль"

        # 2. Check if new wallet is in blacklist
        from app.repositories.blacklist_repository import BlacklistRepository
        blacklist_repo = BlacklistRepository(self.session)
        blacklisted = await blacklist_repo.find_by_wallet(new_wallet_address)
        if blacklisted:
            logger.warning(
                f"User {user_id} tried to change wallet to blacklisted address: {new_wallet_address}"
            )
            return False, "Этот адрес кошелька заблокирован в системе"

        # 3. Check uniqueness
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

            # Invalidate cache after successful commit
            if redis_client:
                try:
                    from app.utils.cache_invalidation import invalidate_user_cache_from_model
                    await invalidate_user_cache_from_model(redis_client, user)
                except Exception as cache_error:
                    # Don't fail the operation if cache invalidation fails
                    logger.warning(
                        f"Failed to invalidate cache for user {user_id} after wallet change: {cache_error}"
                    )

            logger.info(
                f"User {user_id} changed wallet from {old_wallet} to {new_wallet_address}"
            )
            return True, ""
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(
                f"Integrity constraint violation when changing wallet for user {user_id}: {e}",
                exc_info=True
            )
            return False, "Wallet address is already in use or violates database constraints"
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                f"Database error when changing wallet for user {user_id}: {e}",
                exc_info=True
            )
            return False, f"Database error: {str(e)}"
