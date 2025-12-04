"""
UserAction repository.

Data access layer for UserAction model.
"""

from datetime import timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_action import UserAction
from app.repositories.base import BaseRepository
from app.utils.datetime_utils import utc_now


class UserActionRepository(BaseRepository[UserAction]):
    """UserAction repository with specific queries."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize user action repository."""
        super().__init__(UserAction, session)

    async def get_by_user(
        self, user_id: int, action_type: str | None = None
    ) -> list[UserAction]:
        """
        Get actions by user.

        Args:
            user_id: User ID
            action_type: Optional action type filter

        Returns:
            List of user actions
        """
        filters: dict[str, int | str] = {"user_id": user_id}
        if action_type:
            filters["action_type"] = action_type

        return await self.find_by(**filters)

    async def get_by_type(
        self, action_type: str
    ) -> list[UserAction]:
        """
        Get actions by type.

        Args:
            action_type: Action type

        Returns:
            List of actions
        """
        return await self.find_by(action_type=action_type)

    async def cleanup_old_actions(
        self, days: int = 7
    ) -> int:
        """
        Delete actions older than specified days.

        Args:
            days: Number of days (default: 7)

        Returns:
            Number of deleted actions
        """
        cutoff_date = utc_now() - timedelta(days=days)

        stmt = delete(UserAction).where(UserAction.created_at < cutoff_date)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount
