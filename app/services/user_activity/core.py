"""
User Activity Service - Core Module.

Base class with configuration and fundamental logging methods.
"""

from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_activity import UserActivity
from app.repositories.user_activity_repository import (
    UserActivityRepository,
)


class UserActivityServiceCore:
    """Core service with configuration and basic logging methods."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service."""
        self.session = session
        self.repo = UserActivityRepository(session)

    # ============ CONFIGURATION ============

    # Maximum records to keep (older will be deleted)
    MAX_RECORDS = 100000

    # Days to keep records
    RETENTION_DAYS = 30

    # ============ BASIC LOGGING METHODS ============

    async def log_safe(
        self,
        telegram_id: int,
        activity_type: str,
        user_id: int | None = None,
        description: str | None = None,
        message_text: str | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> UserActivity | None:
        """
        Safely log activity without raising exceptions.
        Use this for non-critical logging.

        Returns:
            Created activity record or None on error
        """
        try:
            return await self.log(
                telegram_id=telegram_id,
                activity_type=activity_type,
                user_id=user_id,
                description=description,
                message_text=message_text,
                extra_data=extra_data,
            )
        except Exception as e:
            # Log but don't raise - non-blocking
            logger.debug(f"Activity logging skipped: {e}")
            return None

    async def log(
        self,
        telegram_id: int,
        activity_type: str,
        user_id: int | None = None,
        description: str | None = None,
        message_text: str | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> UserActivity:
        """
        Log any user activity.

        Args:
            telegram_id: User's Telegram ID
            activity_type: Type from ActivityType
            user_id: Internal user ID if known
            description: Human-readable description
            message_text: Full message text
            extra_data: Additional JSON data

        Returns:
            Created activity record
        """
        try:
            activity = await self.repo.log_activity(
                telegram_id=telegram_id,
                activity_type=activity_type,
                user_id=user_id,
                description=description,
                message_text=message_text,
                extra_data=extra_data,
            )
            return activity
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")
            raise
