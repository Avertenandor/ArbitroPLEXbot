"""
Reward session management module.

Handles CRUD operations for reward sessions including creation, updates,
deletion, and retrieval of reward sessions.
"""

from datetime import datetime
from decimal import Decimal

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reward_session import RewardSession
from app.repositories.deposit_reward_repository import DepositRewardRepository
from app.repositories.reward_session_repository import RewardSessionRepository


class RewardSessionManager:
    """Manages reward session CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize reward session manager.

        Args:
            session: Database session
        """
        self.session = session
        self.session_repo = RewardSessionRepository(session)
        self.reward_repo = DepositRewardRepository(session)

    async def create_session(
        self,
        name: str,
        reward_rates: dict[int, Decimal],
        start_date: datetime,
        end_date: datetime,
        created_by: int,
    ) -> tuple[RewardSession | None, str | None]:
        """
        Create new reward session.

        Args:
            name: Session name
            reward_rates: Dict of {level: rate} (e.g., {1: 1.117})
            start_date: Start date
            end_date: End date
            created_by: Admin ID who created session

        Returns:
            Tuple of (session, error_message)
        """
        # Validate dates
        if start_date >= end_date:
            return None, "Дата начала должна быть раньше даты окончания"

        # Validate reward rates for all 5 levels
        for level in range(1, 6):
            if level not in reward_rates or reward_rates[level] < 0:
                return None, f"Некорректная ставка для уровня {level}"

        # Create session
        session = await self.session_repo.create(
            name=name,
            reward_rate_level_1=reward_rates[1],
            reward_rate_level_2=reward_rates[2],
            reward_rate_level_3=reward_rates[3],
            reward_rate_level_4=reward_rates[4],
            reward_rate_level_5=reward_rates[5],
            start_date=start_date,
            end_date=end_date,
            is_active=True,
            created_by=created_by,
        )

        await self.session.commit()

        logger.info(
            "Reward session created",
            extra={
                "session_id": session.id,
                "name": name,
                "created_by": created_by,
            },
        )

        return session, None

    async def update_session(
        self,
        session_id: int,
        name: str | None = None,
        reward_rates: dict[int, Decimal] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        is_active: bool | None = None,
    ) -> tuple[bool, str | None]:
        """
        Update reward session.

        Args:
            session_id: Session ID
            name: New name (optional)
            reward_rates: New rates (optional)
            start_date: New start date (optional)
            end_date: New end date (optional)
            is_active: New active status (optional)

        Returns:
            Tuple of (success, error_message)
        """
        session_obj = await self.session_repo.get_by_id(session_id)

        if not session_obj:
            return False, "Сессия не найдена"

        # Build update dict
        updates = {}
        if name:
            updates["name"] = name
        if start_date:
            updates["start_date"] = start_date
        if end_date:
            updates["end_date"] = end_date
        if is_active is not None:
            updates["is_active"] = is_active

        # Update reward rates if provided
        if reward_rates:
            for level, rate in reward_rates.items():
                updates[f"reward_rate_level_{level}"] = rate

        # Apply updates
        if updates:
            await self.session_repo.update(session_id, **updates)

        # Validate dates
        updated = await self.session_repo.get_by_id(session_id)
        if updated and updated.start_date >= updated.end_date:
            await self.session.rollback()
            return False, "Дата начала должна быть раньше даты окончания"

        await self.session.commit()

        logger.info(
            "Reward session updated", extra={"session_id": session_id}
        )

        return True, None

    async def delete_session(
        self, session_id: int
    ) -> tuple[bool, str | None]:
        """
        Delete reward session (only if no rewards calculated).

        Args:
            session_id: Session ID

        Returns:
            Tuple of (success, error_message)
        """
        # Check if rewards have been calculated (use SQL COUNT to avoid loading all records)
        rewards_count = await self.reward_repo.count(
            reward_session_id=session_id
        )

        if rewards_count > 0:
            return False, (
                f"Невозможно удалить сессию с {rewards_count} "
                f"начисленными наградами. "
                f"Деактивируйте сессию вместо удаления."
            )

        # Delete session
        await self.session_repo.delete(session_id)
        await self.session.commit()

        logger.info(
            "Reward session deleted", extra={"session_id": session_id}
        )

        return True, None

    async def get_all_sessions(self) -> list[RewardSession]:
        """
        Get all reward sessions.

        Returns:
            List of all reward sessions
        """
        return await self.session_repo.find_all()

    async def get_active_sessions(self) -> list[RewardSession]:
        """
        Get active reward sessions.

        Returns:
            List of active reward sessions
        """
        return await self.session_repo.get_active_sessions()

    async def get_session_by_id(
        self, session_id: int
    ) -> RewardSession | None:
        """
        Get reward session by ID.

        Args:
            session_id: Session ID

        Returns:
            Reward session or None if not found
        """
        return await self.session_repo.get_by_id(session_id)
