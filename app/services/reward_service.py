"""
Reward service - Main service facade.

This service acts as a facade that delegates to specialized modules
for better code organization and maintainability. All functionality
is preserved and backward compatibility is maintained.

Module structure:
- reward/session_manager: Session CRUD operations
- reward/session_reward_processor: Session-based reward calculations
- reward/individual_reward_processor: Individual deposit reward processing
- reward/reward_balance_handler: Balance crediting and accounting
- reward/user_rewards: User-specific reward queries
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deposit_reward import DepositReward
from app.models.reward_session import RewardSession
from app.services.base_service import BaseService
from app.services.reward.individual_reward_processor import (
    IndividualRewardProcessor,
)
from app.services.reward.reward_balance_handler import RewardBalanceHandler
from app.services.reward.session_manager import RewardSessionManager
from app.services.reward.session_reward_processor import SessionRewardProcessor
from app.services.reward.user_rewards import UserRewardManager


class RewardService(BaseService):
    """
    Reward service for managing reward sessions and calculations.

    This is a facade that delegates to specialized modules for better
    code organization. All public methods maintain backward compatibility.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize reward service and all sub-components."""
        super().__init__(session)

        # Initialize all specialized components
        self.session_manager = RewardSessionManager(session)
        self.session_processor = SessionRewardProcessor(session)
        self.individual_processor = IndividualRewardProcessor(session)
        self.balance_handler = RewardBalanceHandler(session)
        self.user_rewards = UserRewardManager(session)

    # ========================================================================
    # SESSION MANAGEMENT (delegates to RewardSessionManager)
    # ========================================================================

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
        return await self.session_manager.create_session(
            name, reward_rates, start_date, end_date, created_by
        )

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
        return await self.session_manager.update_session(
            session_id, name, reward_rates, start_date, end_date, is_active
        )

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
        return await self.session_manager.delete_session(session_id)

    async def get_all_sessions(self) -> list[RewardSession]:
        """Get all reward sessions."""
        return await self.session_manager.get_all_sessions()

    async def get_active_sessions(self) -> list[RewardSession]:
        """Get active reward sessions."""
        return await self.session_manager.get_active_sessions()

    async def get_session_by_id(
        self, session_id: int
    ) -> RewardSession | None:
        """Get reward session by ID."""
        return await self.session_manager.get_session_by_id(session_id)

    # ========================================================================
    # SESSION-BASED REWARD CALCULATION (delegates to SessionRewardProcessor)
    # ========================================================================

    async def calculate_rewards_for_session(
        self, session_id: int
    ) -> tuple[bool, int, Decimal, str | None]:
        """
        Calculate rewards for session.

        CRITICAL: Respects ROI cap (500% for level 1).
        Skips deposits with earnings_blocked flag.

        Args:
            session_id: Session ID

        Returns:
            Tuple of (success, rewards_calculated, total_amount, error)
        """
        return await self.session_processor.calculate_rewards_for_session(
            session_id, self.balance_handler
        )

    async def get_session_statistics(
        self, session_id: int
    ) -> dict:
        """
        Get session statistics.

        Uses SQL aggregation to avoid OOM on large datasets.

        Args:
            session_id: Session ID

        Returns:
            Dict with comprehensive session stats
        """
        return await self.session_processor.get_session_statistics(session_id)

    # ========================================================================
    # INDIVIDUAL REWARD CALCULATION (delegates to IndividualRewardProcessor)
    # ========================================================================

    async def calculate_individual_rewards(self) -> None:
        """
        Calculate rewards for deposits that are due for accrual.

        This method processes individual deposits based on their
        next_accrual_at timestamp and corridor settings.
        """
        return await self.individual_processor.calculate_individual_rewards(
            self.balance_handler
        )

    # ========================================================================
    # USER REWARD QUERIES (delegates to UserRewardManager)
    # ========================================================================

    async def get_user_unpaid_rewards(
        self, user_id: int
    ) -> list[DepositReward]:
        """Get unpaid rewards for user."""
        return await self.user_rewards.get_user_unpaid_rewards(user_id)

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
        return await self.user_rewards.mark_rewards_as_paid(reward_ids, tx_hash)

    # ========================================================================
    # INTERNAL HELPER METHODS (delegates to RewardBalanceHandler)
    # ========================================================================

    async def _credit_roi_to_balance(
        self,
        user_id: int,
        reward_amount: Decimal,
        deposit_id: int,
    ) -> None:
        """
        Credit ROI reward to user's internal balance and create transaction.

        This method is kept for backward compatibility with any external
        code that might call it directly.

        Args:
            user_id: User ID receiving the reward
            reward_amount: Reward amount to credit
            deposit_id: Source deposit ID (for reference linking)
        """
        return await self.balance_handler.credit_roi_to_balance(
            user_id, reward_amount, deposit_id
        )
