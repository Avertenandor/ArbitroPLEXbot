"""
User reward query module.

Handles queries and operations related to user-specific rewards,
including fetching unpaid rewards and marking rewards as paid.
"""

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deposit_reward import DepositReward
from app.repositories.deposit_reward_repository import DepositRewardRepository


class UserRewardManager:
    """Manages user-specific reward operations."""

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize user reward manager.

        Args:
            session: Database session
        """
        self.session = session
        self.reward_repo = DepositRewardRepository(session)

    async def get_user_unpaid_rewards(
        self, user_id: int
    ) -> list[DepositReward]:
        """
        Get unpaid rewards for user.

        Args:
            user_id: User ID

        Returns:
            List of unpaid rewards
        """
        return await self.reward_repo.get_unpaid_by_user(user_id)

    async def mark_rewards_as_paid(
        self, reward_ids: list[int], tx_hash: str
    ) -> tuple[bool, int, str | None]:
        """
        Mark rewards as paid (bulk operation).

        Args:
            reward_ids: List of reward IDs
            tx_hash: Transaction hash

        Returns:
            Tuple of (success, updated_count, error_message)
        """
        updated = 0

        for reward_id in reward_ids:
            result = await self.reward_repo.update(
                reward_id, paid=True, tx_hash=tx_hash
            )
            if result:
                updated += 1

        await self.session.commit()

        logger.info(
            "Rewards marked as paid",
            extra={
                "reward_ids": reward_ids,
                "tx_hash": tx_hash,
                "updated": updated,
            },
        )

        return True, updated, None
