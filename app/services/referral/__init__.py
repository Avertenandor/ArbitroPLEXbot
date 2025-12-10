"""
Referral services package.

Contains modular services for referral processing:
- config: Configuration constants (REFERRAL_DEPTH, REFERRAL_RATES)
- chain_manager: Handles referral chain operations
- earnings_manager: Manages earnings and payments
- query_manager: Handles referral queries
- statistics: Provides analytics and statistics
- referral_reward_processor: Processes rewards
- referral_notifications: Handles notifications
"""

from app.services.referral.chain_manager import ReferralChainManager
from app.services.referral.config import REFERRAL_DEPTH, REFERRAL_RATES
from app.services.referral.earnings_manager import ReferralEarningsManager
from app.services.referral.query_manager import ReferralQueryManager
from app.services.referral.referral_reward_processor import (
    ProcessResult,
    ReferralRewardProcessor,
    RewardType,
)
from app.services.referral.statistics import ReferralStatisticsManager


__all__ = [
    # Configuration
    "REFERRAL_DEPTH",
    "REFERRAL_RATES",
    # Managers
    "ReferralChainManager",
    "ReferralEarningsManager",
    "ReferralQueryManager",
    "ReferralStatisticsManager",
    # Reward processing
    "ReferralRewardProcessor",
    "ProcessResult",
    "RewardType",
]
