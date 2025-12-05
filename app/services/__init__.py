"""
Services.

Business logic layer.
"""

# Base Service Infrastructure
# Core Services
# Support & Admin Services
from app.services.admin_service import AdminService
from app.services.base_service import (
    BaseService,
    ServiceResult,
    log_operation,
    transaction,
)
from app.services.blacklist_service import BlacklistService

# Blockchain Service
from app.services.blockchain_service import (
    BlockchainService,
    get_blockchain_service,
    init_blockchain_service,
)
from app.services.deposit_service import DepositService
from app.services.deposit_validation_service import DepositValidationService

# Additional Services
from app.services.finpass_recovery_service import (
    FinpassRecoveryService,
)

# PART5 Critical Services
from app.services.notification_retry_service import (
    NotificationRetryService,
)
# Updated to use modular notification service
from app.services.notification import NotificationService
from app.services.payment_retry_service import PaymentRetryService

# Referral Services
from app.services.referral import (
    ProcessResult,
    ReferralRewardProcessor,
    RewardType,
)
from app.services.referral_service import ReferralService

# Reward Services
from app.services.reward import RewardCalculator
from app.services.reward_service import RewardService
from app.services.support_service import SupportService
from app.services.transaction_service import TransactionService
from app.services.user_notification_service import UserNotificationService
# Updated to use modular user service
from app.services.user import UserService
from app.services.wallet_admin_service import WalletAdminService

# Withdrawal Services
from app.services.withdrawal import (
    ValidationResult,
    WithdrawalBalanceManager,
    WithdrawalValidator,
)
from app.services.withdrawal_service import WithdrawalService

__all__ = [
    # Base Infrastructure
    "BaseService",
    "ServiceResult",
    "transaction",
    "log_operation",
    # Referral Package
    "ReferralRewardProcessor",
    "ProcessResult",
    "RewardType",
    # Reward Package
    "RewardCalculator",
    # Withdrawal Package
    "WithdrawalBalanceManager",
    "WithdrawalValidator",
    "ValidationResult",
    # Core
    "DepositService",
    "NotificationService",
    "DepositValidationService",
    "ReferralService",
    "RewardService",
    "TransactionService",
    "UserService",
    "UserNotificationService",
    "WithdrawalService",
    # PART5 Critical
    "NotificationRetryService",
    "PaymentRetryService",
    # Support & Admin
    "AdminService",
    "BlacklistService",
    "SupportService",
    # Blockchain
    "BlockchainService",
    "get_blockchain_service",
    "init_blockchain_service",
    # Additional
    "FinpassRecoveryService",
    "WalletAdminService",
]
