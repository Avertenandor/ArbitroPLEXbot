"""
Referral service.

Manages referral chains, relationships, and reward processing.

This is the main service that delegates to specialized modules for better organization:
- chain_manager: Handles referral chain operations
- earnings_manager: Manages earnings and payments
- query_manager: Handles referral queries
- statistics: Provides analytics and statistics
- referral_reward_processor: Processes rewards (already modularized)
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.referral_earning_repository import (
    ReferralEarningRepository,
)
from app.repositories.referral_repository import ReferralRepository
from app.repositories.user_repository import UserRepository
from app.services.base_service import BaseService
from app.services.referral.chain_manager import ReferralChainManager
from app.services.referral.config import REFERRAL_DEPTH, REFERRAL_RATES
from app.services.referral.earnings_manager import ReferralEarningsManager
from app.services.referral.query_manager import ReferralQueryManager
from app.services.referral.referral_reward_processor import (
    ReferralRewardProcessor,
)
from app.services.referral.statistics import ReferralStatisticsManager

if TYPE_CHECKING:
    from aiogram import Bot


class ReferralService(BaseService):
    """Referral service for managing referral chains and rewards."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize referral service and specialized managers."""
        super().__init__(session)
        self.referral_repo = ReferralRepository(session)
        self.earning_repo = ReferralEarningRepository(session)
        self.user_repo = UserRepository(session)

        # Initialize specialized managers
        self.chain_manager = ReferralChainManager(session)
        self.earnings_manager = ReferralEarningsManager(session)
        self.query_manager = ReferralQueryManager(session)
        self.statistics_manager = ReferralStatisticsManager(session)
        self.reward_processor = ReferralRewardProcessor(session)

    async def get_referral_chain(
        self, user_id: int, depth: int = REFERRAL_DEPTH
    ) -> list[User]:
        """
        Get referral chain (PostgreSQL CTE optimized).

        Uses recursive CTE to efficiently fetch entire referral chain.

        Args:
            user_id: User ID
            depth: Chain depth to retrieve

        Returns:
            List of users from direct referrer to Nth level
        """
        return await self.chain_manager.get_referral_chain(user_id, depth)

    async def create_referral_relationships(
        self, new_user_id: int, direct_referrer_id: int
    ) -> tuple[bool, str | None]:
        """
        Create referral relationships for new user.

        Creates multi-level referral chain (up to REFERRAL_DEPTH levels).

        Args:
            new_user_id: New user ID
            direct_referrer_id: Direct referrer ID

        Returns:
            Tuple of (success, error_message)
        """
        return await self.chain_manager.create_referral_relationships(
            new_user_id, direct_referrer_id
        )

    async def process_referral_rewards(
        self, user_id: int, deposit_amount: Decimal, bot: "Bot | None" = None
    ) -> tuple[bool, Decimal, str | None]:
        """
        Process referral rewards for a deposit.

        Creates earning records for all referrers in chain.

        Args:
            user_id: User who made deposit
            deposit_amount: Deposit amount
            bot: Optional bot instance for sending notifications

        Returns:
            Tuple of (success, total_rewards, error_message)
        """
        result = await self.reward_processor.process_rewards(
            user_id=user_id,
            amount=deposit_amount,
            reward_type="deposit",
        )

        # Send notifications if bot provided
        if bot and result.notifications:
            await self._send_reward_notifications(bot, result.notifications)

        return result.success, result.total_rewards, result.error_message

    async def process_roi_referral_rewards(
        self, user_id: int, roi_amount: Decimal, bot: "Bot | None" = None
    ) -> tuple[bool, Decimal, str | None]:
        """
        Process referral rewards for ROI accrual.

        Args:
            user_id: User who received ROI
            roi_amount: ROI amount
            bot: Optional bot instance for sending notifications

        Returns:
            Tuple of (success, total_rewards, error_message)
        """
        result = await self.reward_processor.process_rewards(
            user_id=user_id,
            amount=roi_amount,
            reward_type="roi",
        )

        # Send notifications if bot provided (only for significant amounts)
        if bot and result.notifications:
            # Filter small ROI notifications to avoid spam
            significant = [n for n in result.notifications if n.reward_amount >= 0.01]
            if significant:
                await self._send_reward_notifications(bot, significant)

        return result.success, result.total_rewards, result.error_message

    async def _send_reward_notifications(
        self, bot: "Bot", notifications: list
    ) -> None:
        """Send reward notifications to referrers."""
        from app.services.referral.referral_notifications import (
            notify_referral_reward,
        )

        for notif in notifications:
            try:
                await notify_referral_reward(
                    bot=bot,
                    referrer_telegram_id=notif.referrer_telegram_id,
                    reward_amount=notif.reward_amount,
                    level=notif.level,
                    source_username=notif.source_username,
                    source_telegram_id=notif.source_telegram_id,
                    reward_type=notif.reward_type,
                )
            except Exception as e:
                logger.warning(f"Failed to send reward notification: {e}")

    async def get_referrals_by_level(
        self, user_id: int, level: int, page: int = 1, limit: int = 10
    ) -> dict:
        """
        Get user's referrals by level.

        Args:
            user_id: User ID
            level: Referral level (1-3)
            page: Page number
            limit: Items per page

        Returns:
            Dict with referrals, total, page, pages
        """
        return await self.query_manager.get_referrals_by_level(
            user_id, level, page, limit
        )

    async def get_pending_earnings(
        self, user_id: int, page: int = 1, limit: int = 10
    ) -> dict:
        """
        Get pending (unpaid) earnings for user.

        Uses SQL aggregation to avoid OOM on large datasets.

        Args:
            user_id: User ID
            page: Page number
            limit: Items per page

        Returns:
            Dict with earnings, total, total_amount, page, pages
        """
        return await self.earnings_manager.get_pending_earnings(
            user_id, page, limit
        )

    async def mark_earning_as_paid(
        self, earning_id: int, tx_hash: str
    ) -> tuple[bool, str | None]:
        """
        Mark earning as paid (called by payment processor).

        Args:
            earning_id: Earning ID
            tx_hash: Transaction hash

        Returns:
            Tuple of (success, error_message)
        """
        return await self.earnings_manager.mark_earning_as_paid(
            earning_id, tx_hash
        )

    async def get_referral_stats(self, user_id: int) -> dict:
        """
        Get referral statistics for user.

        Args:
            user_id: User ID

        Returns:
            Dict with referral counts and earnings
        """
        return await self.statistics_manager.get_referral_stats(user_id)

    async def get_referral_leaderboard(self, limit: int = 10) -> dict:
        """
        Get referral leaderboard.

        Args:
            limit: Number of top users to return

        Returns:
            Dict with by_referrals and by_earnings lists
        """
        return await self.statistics_manager.get_referral_leaderboard(limit)

    async def get_user_leaderboard_position(self, user_id: int) -> dict:
        """
        Get user's position in leaderboard.

        Args:
            user_id: User ID

        Returns:
            Dict with referral_rank, earnings_rank, total_users
        """
        return await self.statistics_manager.get_user_leaderboard_position(user_id)

    async def get_platform_referral_stats(self) -> dict:
        """
        Get platform-wide referral statistics.

        Uses SQL aggregation to avoid OOM on large datasets.

        Returns:
            Dict with total referrals, earnings breakdown
        """
        return await self.statistics_manager.get_platform_referral_stats()

    async def get_daily_earnings_stats(
        self, user_id: int, days: int = 7
    ) -> dict:
        """
        Get daily earnings statistics for user.

        Args:
            user_id: User ID
            days: Number of days to retrieve (default 7)

        Returns:
            Dict with daily earnings breakdown
        """
        return await self.statistics_manager.get_daily_earnings_stats(
            user_id, days
        )

    async def get_referral_conversion_stats(self, user_id: int) -> dict:
        """
        Get referral conversion statistics.

        Shows how many referrals made deposits and average deposit amount.

        Args:
            user_id: User ID

        Returns:
            Dict with conversion stats
        """
        return await self.statistics_manager.get_referral_conversion_stats(user_id)

    async def get_referral_activity_stats(self, user_id: int) -> dict:
        """
        Get referral activity statistics.

        Shows active vs inactive referrals.

        Args:
            user_id: User ID

        Returns:
            Dict with activity stats
        """
        return await self.statistics_manager.get_referral_activity_stats(user_id)

    async def get_my_referrers(self, user_id: int) -> dict:
        """
        Get who invited this user (their referrer chain).

        Shows the user's position in the referral structure.

        Args:
            user_id: User ID

        Returns:
            Dict with referrer info
        """
        return await self.query_manager.get_my_referrers(user_id)
