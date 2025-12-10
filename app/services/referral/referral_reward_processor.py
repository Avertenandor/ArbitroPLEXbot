"""
Referral reward processor.

Consolidated processor for handling referral rewards from both deposits and ROI.
Eliminates duplication between deposit and ROI reward processing.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

from loguru import logger
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.referral import Referral
from app.models.user import User
from app.repositories.referral_earning_repository import (
    ReferralEarningRepository,
)
from app.repositories.referral_repository import ReferralRepository
from app.repositories.user_repository import UserRepository


# Referral system configuration
REFERRAL_DEPTH = 3
REFERRAL_RATES = {
    1: Decimal("0.05"),  # 5% for level 1 (direct referrals)
    2: Decimal("0.05"),  # 5% for level 2
    3: Decimal("0.05"),  # 5% for level 3
}

# Type alias for reward types
RewardType = Literal["deposit", "roi"]


@dataclass
class RewardNotification:
    """Data for sending reward notification."""

    referrer_telegram_id: int
    reward_amount: Decimal
    level: int
    source_username: str | None
    source_telegram_id: int
    reward_type: str


@dataclass
class ProcessResult:
    """Result of reward processing."""

    success: bool
    total_rewards: Decimal
    error_message: str | None = None
    rewards_count: int = 0
    notifications: list[RewardNotification] = field(default_factory=list)


class ReferralRewardProcessor:
    """
    Consolidated processor for referral rewards.

    Handles reward processing for both deposit and ROI events,
    eliminating ~95% duplication between the two processes.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize referral reward processor.

        Args:
            session: Async database session
        """
        self.session = session
        self.referral_repo = ReferralRepository(session)
        self.earning_repo = ReferralEarningRepository(session)
        self.user_repo = UserRepository(session)

    async def process_rewards(
        self,
        user_id: int,
        amount: Decimal,
        reward_type: RewardType,
        source_id: int | None = None,
        tx_hash: str | None = None,
    ) -> ProcessResult:
        """
        Process referral rewards for a user action (deposit or ROI).

        This method consolidates the logic for both deposit and ROI reward processing,
        eliminating duplication while maintaining all functionality.

        Args:
            user_id: User who triggered the reward (made deposit or received ROI)
            amount: Amount to calculate rewards from
            reward_type: Type of reward - "deposit" or "roi"
            source_id: Optional source transaction ID
            tx_hash: Optional blockchain transaction hash

        Returns:
            ProcessResult with success status, total rewards, and error message if any
        """
        # Get all referral relationships for this user (where they are the referral)
        relationships = await self._get_referral_chain(user_id)

        if not relationships:
            logger.debug(
                "No referrers found for user",
                extra={"user_id": user_id, "reward_type": reward_type},
            )
            return ProcessResult(
                success=True,
                total_rewards=Decimal("0"),
                error_message=None,
                rewards_count=0,
            )

        # Get source user info for notifications
        source_user = await self.user_repo.get_by_id(user_id)
        source_username = source_user.username if source_user else None
        source_telegram_id = source_user.telegram_id if source_user else 0

        total_rewards = Decimal("0")
        rewards_count = 0
        notifications: list[RewardNotification] = []

        # Determine tx_hash based on reward type
        if tx_hash is None:
            tx_hash = f"internal_balance_{reward_type}"

        # Process each referrer in the chain
        for relationship in relationships:
            level = relationship.level
            reward_amount = self._calculate_level_reward(amount, level)

            if reward_amount <= 0:
                continue

            # Create the reward record and get referrer info
            referrer_info = await self._create_reward_record(
                relationship=relationship,
                reward_amount=reward_amount,
                tx_hash=tx_hash,
                source_id=source_id,
                user_id=user_id,
                reward_type=reward_type,
            )

            if referrer_info:
                total_rewards += reward_amount
                rewards_count += 1

                # Add notification data
                notifications.append(RewardNotification(
                    referrer_telegram_id=referrer_info["telegram_id"],
                    reward_amount=reward_amount,
                    level=level,
                    source_username=source_username,
                    source_telegram_id=source_telegram_id,
                    reward_type=reward_type,
                ))

        # Commit all changes
        await self.session.commit()

        logger.info(
            "Referral rewards processed",
            extra={
                "user_id": user_id,
                "reward_type": reward_type,
                "total_rewards": str(total_rewards),
                "rewards_count": rewards_count,
            },
        )

        return ProcessResult(
            success=True,
            total_rewards=total_rewards,
            error_message=None,
            rewards_count=rewards_count,
            notifications=notifications,
        )

    async def _get_referral_chain(
        self, user_id: int, levels: int = REFERRAL_DEPTH
    ) -> list[Referral]:
        """
        Get referral chain for a user.

        Retrieves all referral relationships where the user is the referral
        (i.e., they were referred by others), up to the specified number of levels.

        Args:
            user_id: User ID to get referral chain for
            levels: Maximum number of levels to retrieve (default: REFERRAL_DEPTH)

        Returns:
            List of Referral objects ordered by level
        """
        relationships = await self.referral_repo.get_referrals_for_user(user_id)

        # Filter by level and sort
        relationships = [r for r in relationships if r.level <= levels]
        relationships.sort(key=lambda r: r.level)

        return relationships

    def _calculate_level_reward(
        self, amount: Decimal, level: int
    ) -> Decimal:
        """
        Calculate reward amount for a specific referral level.

        Args:
            amount: Base amount to calculate reward from
            level: Referral level (1-3)

        Returns:
            Calculated reward amount (0 if level not configured)
        """
        rate = REFERRAL_RATES.get(level, Decimal("0"))

        if rate == Decimal("0"):
            return Decimal("0")

        return amount * rate

    async def _create_reward_record(
        self,
        relationship: Referral,
        reward_amount: Decimal,
        tx_hash: str,
        source_id: int | None,
        user_id: int,
        reward_type: RewardType,
    ) -> dict | None:
        """
        Create a reward record and update referrer balance.

        Args:
            relationship: Referral relationship object
            reward_amount: Amount to reward
            tx_hash: Transaction hash for the earning record
            source_id: Optional source transaction ID
            user_id: User ID who triggered the reward
            reward_type: Type of reward ("deposit" or "roi")

        Returns:
            Dict with referrer info if created, None otherwise
        """
        # Get referrer info for notifications
        referrer = await self.user_repo.get_by_id(relationship.referrer_id)
        if not referrer:
            logger.warning(
                "Referrer not found for reward",
                extra={
                    "referrer_id": relationship.referrer_id,
                    "referral_id": relationship.id,
                    "reward_type": reward_type,
                },
            )
            return None

        # R9-2: Atomic update to prevent race conditions
        stmt = (
            update(User)
            .where(User.id == relationship.referrer_id)
            .values(
                balance=User.balance + reward_amount,
                total_earned=User.total_earned + reward_amount,
            )
        )
        result = await self.session.execute(stmt)

        if result.rowcount == 0:
            return None

        # Create earning record
        await self.earning_repo.create(
            referral_id=relationship.id,
            amount=reward_amount,
            paid=True,  # Paid to internal balance
            tx_hash=tx_hash,
        )

        # Update total earned in relationship
        relationship.total_earned += reward_amount
        self.session.add(relationship)

        # Flush to ensure changes are queued
        await self.session.flush()

        logger.info(
            f"Referral {reward_type} reward created",
            extra={
                "referrer_id": relationship.referrer_id,
                "referral_user_id": user_id,
                "level": relationship.level,
                "rate": str(REFERRAL_RATES.get(relationship.level, Decimal("0"))),
                "amount": str(reward_amount),
                "source": reward_type,
            },
        )

        return {"telegram_id": referrer.telegram_id}
