"""
User loader utilities for bot handlers.

Provides unified patterns for loading users and admins from database.
"""


from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin
from app.models.user import User


class UserLoader:
    """Unified user loading utilities."""

    @staticmethod
    async def get_user_by_telegram_id(
        session: AsyncSession,
        telegram_id: int
    ) -> User | None:
        """
        Get user by Telegram ID.

        Args:
            session: Database session
            telegram_id: User's Telegram ID

        Returns:
            User object or None if not found
        """
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_with_fallback(
        session: AsyncSession,
        telegram_id: int,
        state: FSMContext | None = None
    ) -> User | None:
        """
        Get user from state data (if available) or database.

        Common pattern: Check if user was cached in FSM state,
        otherwise fall back to database lookup.

        Args:
            session: Database session
            telegram_id: User's Telegram ID
            state: FSM context (may contain cached user)

        Returns:
            User object or None if not found
        """
        # Try to get from state data first (if state provided)
        if state:
            data = await state.get_data()
            user = data.get("user")
            if user and isinstance(user, User) and user.telegram_id == telegram_id:
                return user

        # Fallback to database lookup
        return await UserLoader.get_user_by_telegram_id(session, telegram_id)

    @staticmethod
    async def search_user(
        session: AsyncSession,
        query: str
    ) -> User | None:
        """
        Search user by telegram_id, wallet address, or username.

        Tries multiple search strategies:
        1. If starts with "0x" and length 42: search by wallet address
        2. If numeric: search by telegram_id
        3. Otherwise: search by username (strips @ if present)

        Args:
            session: Database session
            query: Search query (telegram_id, wallet, or username)

        Returns:
            User object or None if not found
        """
        query = query.strip()

        # Search by wallet address (BSC/BEP-20 format)
        if query.startswith("0x") and len(query) == 42:
            stmt = select(User).where(User.wallet_address == query)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

        # Search by telegram_id (numeric)
        if query.isdigit():
            telegram_id = int(query)
            return await UserLoader.get_user_by_telegram_id(session, telegram_id)

        # Search by username (strip @ if present)
        username = query.lstrip("@")
        stmt = select(User).where(User.username == username)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_admin_by_telegram_id(
        session: AsyncSession,
        telegram_id: int
    ) -> Admin | None:
        """
        Get admin by Telegram ID.

        Args:
            session: Database session
            telegram_id: Admin's Telegram ID

        Returns:
            Admin object or None if not found
        """
        stmt = select(Admin).where(Admin.telegram_id == telegram_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


def format_user_label(user: User) -> str:
    """
    Format user label for display.

    Generates a user-friendly label in the format:
    - "@username (ID: telegram_id)" if username exists
    - "ID: telegram_id" if no username

    Args:
        user: User object

    Returns:
        Formatted user label string

    Example:
        >>> format_user_label(user)
        "@john_doe (ID: 123456789)"
    """
    if user.username:
        return f"@{user.username} (ID: {user.telegram_id})"
    return f"ID: {user.telegram_id}"
