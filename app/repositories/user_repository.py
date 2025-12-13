"""
User repository.

Data access layer for User model.
"""

from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

try:
    from redis.asyncio import Redis
except ImportError:
    import redis.asyncio as redis
    Redis = redis.Redis

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """User repository with specific queries."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize user repository."""
        super().__init__(User, session)

    async def get_by_telegram_id(
        self, telegram_id: int
    ) -> User | None:
        """
        Get user by Telegram ID.

        Args:
            telegram_id: Telegram user ID

        Returns:
            User or None
        """
        return await self.get_by(telegram_id=telegram_id)

    async def get_by_wallet_address(
        self, wallet_address: str
    ) -> User | None:
        """
        Get user by wallet address.

        Args:
            wallet_address: Wallet address

        Returns:
            User or None
        """
        return await self.get_by(wallet_address=wallet_address)

    async def find_by_wallet_address(
        self, wallet_address: str
    ) -> User | None:
        """
        Find user by wallet address (case-insensitive).

        Normalizes the address to lowercase before searching.

        Args:
            wallet_address: Wallet address (any case)

        Returns:
            User or None
        """
        if not wallet_address:
            return None
        # Try exact match first
        normalized = wallet_address.lower()
        result = await self.get_by(wallet_address=normalized)
        if result:
            return result
        # Try original case
        return await self.get_by(wallet_address=wallet_address)

    async def get_by_referral_code(
        self, referral_code: str
    ) -> User | None:
        """
        Get user by referral code.

        Args:
            referral_code: Referral code

        Returns:
            User or None
        """
        return await self.get_by(referral_code=referral_code)

    async def get_by_username(
        self, username: str
    ) -> User | None:
        """
        Get user by Telegram username (case-insensitive).

        Args:
            username: Telegram username (without @)

        Returns:
            User or None
        """
        if not username:
            return None
        # Remove @ if present
        clean_username = username.lstrip("@").lower()
        # Search case-insensitive
        stmt = select(User).where(
            User.username.ilike(clean_username)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_referrals(
        self, user_id: int
    ) -> User | None:
        """
        Get user with referrals loaded.

        Args:
            user_id: User ID

        Returns:
            User with referrals or None
        """
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.referrals_as_referrer),
                selectinload(User.referred_users),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_telegram_ids(self) -> list[int]:
        """
        Get all user Telegram IDs.

        WARNING: This loads all IDs into memory. For large datasets,
        use get_telegram_ids_batched() instead.

        Returns:
            List of Telegram IDs
        """
        stmt = select(User.telegram_id).where(User.is_banned is False)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_active_users(self) -> list[User]:
        """
        Get all active (non-banned) users.

        Returns:
            List of active users
        """
        return await self.find_by(is_banned=False)

    async def get_banned_users(self) -> list[User]:
        """
        Get all banned users.

        Returns:
            List of banned users
        """
        return await self.find_by(is_banned=True)

    async def get_verified_users(self) -> list[User]:
        """
        Get all verified users.

        Returns:
            List of verified users
        """
        return await self.find_by(is_verified=True)

    async def get_telegram_ids_batched(self, batch_size: int = 1000):
        """
        Generator for getting telegram_ids in batches to avoid OOM.

        Uses OFFSET/LIMIT to stream data from DB without loading all into memory.

        Args:
            batch_size: Number of IDs per batch

        Yields:
            Batches of telegram IDs
        """
        offset = 0
        while True:
            stmt = (
                select(User.telegram_id)
                .where(User.is_banned == False)  # noqa: E712
                .offset(offset)
                .limit(batch_size)
            )
            result = await self.session.execute(stmt)
            batch = list(result.scalars().all())

            if not batch:
                break

            yield batch
            offset += batch_size

    async def count_verified_users(self) -> int:
        """
        Count verified users.

        Returns:
            Number of verified users
        """
        from sqlalchemy import func

        stmt = select(func.count(User.id)).where(
            User.is_banned == False  # noqa: E712
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def update(
        self,
        id: int,
        for_update: bool = False,
        redis_client: Redis | None = None,
        **data: Any,
    ) -> User | None:
        """
        Update user by ID with cache invalidation.

        Overrides BaseRepository.update() to add Redis cache invalidation.
        When user data is updated, corresponding cache keys are removed.

        Args:
            id: User ID
            for_update: Use SELECT FOR UPDATE to lock row
            redis_client: Optional Redis client for cache invalidation
            **data: Updated data

        Returns:
            Updated user or None if not found

        Example:
            >>> from app.utils.redis_utils import get_redis_client
            >>> redis = await get_redis_client()
            >>> user = await user_repo.update(
            ...     123,
            ...     redis_client=redis,
            ...     is_verified=True
            ... )
            >>> await redis.close()
        """
        # Call parent update method
        user = await super().update(id, for_update=for_update, **data)

        # Invalidate cache if update succeeded and redis client provided
        if user and redis_client:
            try:
                from app.utils.cache_invalidation import invalidate_user_cache_from_model
                await invalidate_user_cache_from_model(redis_client, user)
            except Exception as e:
                # Don't fail the update if cache invalidation fails
                logger.warning(
                    f"Failed to invalidate cache for user {id}: {e}",
                    extra={"user_id": id},
                )

        return user
