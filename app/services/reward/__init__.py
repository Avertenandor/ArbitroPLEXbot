"""
Reward services package.

This package provides modular reward management functionality:
- reward_calculator: Core calculation logic for ROI and rates
- session_manager: CRUD operations for reward sessions
- session_reward_processor: Reward calculation for deposit sessions
- individual_reward_processor: Individual deposit reward processing
- reward_balance_handler: Balance crediting and accounting
- user_rewards: User-specific reward queries

All components are re-exported for easy importing.
"""

from app.services.reward.individual_reward_processor import (
    IndividualRewardProcessor,
)
from app.services.reward.reward_balance_handler import RewardBalanceHandler
from app.services.reward.reward_calculator import RewardCalculator
from app.services.reward.session_manager import RewardSessionManager
from app.services.reward.session_reward_processor import SessionRewardProcessor
from app.services.reward.user_rewards import UserRewardManager

__all__ = [
    "RewardCalculator",
    "RewardSessionManager",
    "SessionRewardProcessor",
    "IndividualRewardProcessor",
    "RewardBalanceHandler",
    "UserRewardManager",
]
