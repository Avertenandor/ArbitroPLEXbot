"""
Database models.

Exports all SQLAlchemy models for easy imports.
"""

# Admin Models
from app.models.admin import Admin
from app.models.admin_action import AdminAction
from app.models.admin_action_escrow import AdminActionEscrow
from app.models.admin_session import AdminSession
from app.models.appeal import Appeal, AppealStatus
from app.models.base import Base

# Security Models
from app.models.blacklist import Blacklist

# Blockchain Cache
from app.models.blockchain_tx_cache import BlockchainTxCache
from app.models.blockchain_sync_state import BlockchainSyncState

# Bonus Credits
from app.models.bonus_credit import BonusCredit

from app.models.deposit import Deposit
from app.models.deposit_corridor_history import DepositCorridorHistory
from app.models.deposit_level_config import DepositLevelConfig
from app.models.deposit_level_version import DepositLevelVersion
from app.models.deposit_reward import DepositReward
from app.models.enums import (
    SupportCategory,
    SupportSender,
    SupportTicketPriority,
    SupportTicketStatus,
    TransactionStatus,
    TransactionType,
    WalletChangeStatus,
    WalletChangeType,
)
from app.models.failed_notification import FailedNotification
from app.models.financial_password_recovery import (
    FinancialPasswordRecovery,
)

# System Models
from app.models.global_settings import GlobalSettings
from app.models.notification_queue_fallback import NotificationQueueFallback

# КРИТИЧНЫЕ модели из PART5
from app.models.payment_retry import PaymentRetry, PaymentType
from app.models.plex_payment import PlexPaymentRequirement, PlexPaymentStatus
from app.models.referral import Referral
from app.models.referral_earning import ReferralEarning

# Reward Models
from app.models.reward_session import RewardSession

# Sponsor Inquiry Models
from app.models.sponsor_inquiry import (
    SponsorInquiry,
    SponsorInquiryMessage,
    SponsorInquiryStatus,
)
from app.models.support_message import SupportMessage

# Support Models
from app.models.support_ticket import SupportTicket
from app.models.transaction import Transaction

# Core Models
from app.models.user import User
from app.models.user_action import UserAction
from app.models.user_fsm_state import UserFsmState

# User Inquiry Models
from app.models.user_inquiry import InquiryMessage, InquiryStatus, UserInquiry
from app.models.user_message_log import UserMessageLog
from app.models.user_notification_settings import UserNotificationSettings
from app.models.user_wallet_history import UserWalletHistory
from app.models.wallet_change_request import WalletChangeRequest

__all__ = [
    # Base
    "Base",
    # Enums
    "TransactionStatus",
    "UserMessageLog",
    "TransactionType",
    "WalletChangeStatus",
    "WalletChangeType",
    "SupportTicketStatus",
    "SupportTicketPriority",
    "SupportCategory",
    "SupportSender",
    "PaymentType",
    # Core Models
    "User",
    "Deposit",
    "DepositCorridorHistory",
    "DepositLevelConfig",
    "DepositLevelVersion",
    "Transaction",
    "Referral",
    # Blockchain Cache
    "BlockchainTxCache",
    "BlockchainSyncState",
    # Bonus Credits
    "BonusCredit",
    # Admin Models
    "Admin",
    "AdminAction",
    "AdminActionEscrow",
    "AdminSession",
    # Security Models
    "Blacklist",
    "FinancialPasswordRecovery",
    "Appeal",
    "AppealStatus",
    # Reward Models
    "RewardSession",
    "DepositReward",
    "ReferralEarning",
    # PART5 Critical Models
    "PaymentRetry",
    "PlexPaymentRequirement",
    "PlexPaymentStatus",
    "FailedNotification",
    "NotificationQueueFallback",  # R11-3: PostgreSQL fallback
    # Support Models
    "SupportTicket",
    "SupportMessage",
    # User Inquiry Models
    "UserInquiry",
    "InquiryMessage",
    "InquiryStatus",
    # Sponsor Inquiry Models
    "SponsorInquiry",
    "SponsorInquiryMessage",
    "SponsorInquiryStatus",
    # System Models
    "GlobalSettings",
    "UserAction",
    "UserFsmState",
    "UserNotificationSettings",
    "UserWalletHistory",
    "WalletChangeRequest",
]
