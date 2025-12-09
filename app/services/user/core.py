"""
Core user service functionality.

Handles basic user retrieval operations and profile management.
"""

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.blacklist_repository import BlacklistRepository
from app.repositories.user_repository import UserRepository


class UserServiceCore:
    """
    Core user service.

    Provides basic user retrieval and profile management methods.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize user service core.

        Args:
            session: Database session
        """
        self.session = session
        self.user_repo = UserRepository(session)
        self.blacklist_repo = BlacklistRepository(session)

    async def get_by_id(self, user_id: int) -> User | None:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User or None
        """
        return await self.user_repo.get_by_id(user_id)

    async def get_user_by_id(self, user_id: int) -> User | None:
        """
        Get user by ID (alias).

        Args:
            user_id: User ID

        Returns:
            User or None
        """
        return await self.get_by_id(user_id)

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
        return await self.user_repo.get_by_telegram_id(
            telegram_id
        )

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
        return await self.user_repo.get_by_referral_code(
            referral_code
        )

    async def get_by_username(
        self, username: str
    ) -> User | None:
        """
        Get user by Telegram username.

        Args:
            username: Telegram username (with or without @)

        Returns:
            User or None
        """
        return await self.user_repo.get_by_username(username)

    async def find_by_id(self, user_id: int) -> User | None:
        """
        Find user by ID (alias for get_by_id).

        Args:
            user_id: User ID

        Returns:
            User or None
        """
        return await self.user_repo.get_by_id(user_id)

    async def find_by_username(self, username: str) -> User | None:
        """
        Find user by username.

        Args:
            username: Username (without @)

        Returns:
            User or None
        """
        users = await self.user_repo.find_by(username=username)
        return users[0] if users else None

    async def find_by_telegram_id(self, telegram_id: int) -> User | None:
        """
        Find user by Telegram ID.

        Args:
            telegram_id: Telegram ID

        Returns:
            User or None
        """
        users = await self.user_repo.find_by(telegram_id=telegram_id)
        return users[0] if users else None

    async def get_by_wallet(self, wallet_address: str) -> User | None:
        """
        Get user by wallet address.

        Args:
            wallet_address: Wallet address

        Returns:
            User or None
        """
        return await self.user_repo.get_by_wallet_address(wallet_address)

    async def update_profile(
        self, user_id: int, **data
    ) -> User | None:
        """
        Update user profile.

        Args:
            user_id: User ID
            **data: Fields to update

        Returns:
            Updated user or None
        """
        # Validate wallet uniqueness (additional check besides DB constraint)
        if "wallet_address" in data:
            wallet_address = data["wallet_address"]
            existing = await self.user_repo.get_by_wallet_address(wallet_address)
            if existing and existing.id != user_id:
                raise ValueError("Wallet address is already used by another user")

        user = await self.user_repo.update(user_id, **data)

        if user:
            await self.session.commit()
            logger.info(
                "User profile updated",
                extra={"user_id": user_id},
            )

        return user

    async def block_earnings(
        self, user_id: int, block: bool = True
    ) -> User | None:
        """
        Block/unblock user earnings.

        Used during financial password recovery.

        Args:
            user_id: User ID
            block: True to block, False to unblock

        Returns:
            Updated user or None
        """
        return await self.update_profile(
            user_id, earnings_blocked=block
        )

    async def ban_user(
        self, user_id: int, ban: bool = True
    ) -> User | None:
        """
        Ban/unban user.

        Args:
            user_id: User ID
            ban: True to ban, False to unban

        Returns:
            Updated user or None
        """
        return await self.update_profile(user_id, is_banned=ban)

    async def unban_user(self, user_id: int) -> dict:
        """
        Unban user.

        Args:
            user_id: User ID

        Returns:
            Result dict with success status
        """
        user = await self.ban_user(user_id, ban=False)
        if user:
            return {"success": True}
        return {"success": False, "error": "User not found"}

    async def get_all_telegram_ids(self) -> list[int]:
        """
        Get all user Telegram IDs.

        WARNING: This loads all IDs into memory. For large datasets
        (e.g., broadcasts), use get_telegram_ids_batched() instead.

        Returns:
            List of Telegram IDs
        """
        return await self.user_repo.get_all_telegram_ids()

    async def get_telegram_ids_batched(self, batch_size: int = 1000):
        """
        Generator for getting telegram_ids in batches to avoid OOM.

        Use this for broadcasts and other operations on large user sets.

        Args:
            batch_size: Number of IDs per batch

        Yields:
            Batches of telegram IDs
        """
        async for batch in self.user_repo.get_telegram_ids_batched(batch_size):
            yield batch

    async def get_total_users(self) -> int:
        """
        Get total number of users.

        Returns:
            Total user count
        """
        return await self.user_repo.count()

    async def get_verified_users(self) -> int:
        """
        Get number of verified users.

        Returns:
            Verified user count
        """
        # Use SQL COUNT to avoid loading all user records
        return await self.user_repo.count(is_verified=True)

    async def count_verified_users(self) -> int:
        """
        Count verified users.

        Returns:
            Number of verified users
        """
        return await self.user_repo.count_verified_users()

    def generate_referral_link(
        self, user: User, bot_username: str | None
    ) -> str:
        """
        Generate referral link for user.

        Uses user's referral_code if available, otherwise falls back to telegram_id.

        Args:
            user: User object
            bot_username: Bot username

        Returns:
            Referral link in format: https://t.me/{bot}?start=ref_{code}
        """
        username = bot_username or "bot"

        # Use referral_code if available, otherwise fallback to telegram_id
        code = user.referral_code if user.referral_code else str(user.telegram_id)

        logger.debug(
            f"Generating referral link for user {user.id}: "
            f"using {'referral_code' if user.referral_code else 'telegram_id'} = {code}"
        )

        return f"https://t.me/{username}?start=ref_{code}"
