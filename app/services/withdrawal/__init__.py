"""
Withdrawal services package.

This package provides modular withdrawal management functionality:
- withdrawal_validator: Validation logic for withdrawal requests
  - withdrawal_validator_core: Main validation logic
  - withdrawal_basic_checks: Basic validation checks
  - withdrawal_plex_checks: PLEX-specific checks
  - withdrawal_security_checks: Security checks (fraud, finpass)
- withdrawal_balance_manager: Balance deduction and restoration
- withdrawal_request_handler: Withdrawal request creation
- withdrawal_lifecycle_handler: Approval, rejection, cancellation
- withdrawal_query_service: Queries and history
- withdrawal_statistics_service: Statistics and reporting
- withdrawal_helpers: Utility functions

All components are re-exported for easy importing.
"""

from app.services.withdrawal.withdrawal_balance_manager import (
    WithdrawalBalanceManager,
)
from app.services.withdrawal.withdrawal_helpers import WithdrawalHelpers
from app.services.withdrawal.withdrawal_lifecycle_handler import (
    WithdrawalLifecycleHandler,
)
from app.services.withdrawal.withdrawal_query_service import (
    WithdrawalQueryService,
)
from app.services.withdrawal.withdrawal_request_handler import (
    WithdrawalRequestHandler,
)
from app.services.withdrawal.withdrawal_statistics_service import (
    WithdrawalStatisticsService,
)
from app.services.withdrawal.withdrawal_validator import (
    ValidationResult,
    WithdrawalValidator,
)


__all__ = [
    "WithdrawalBalanceManager",
    "WithdrawalValidator",
    "ValidationResult",
    "WithdrawalRequestHandler",
    "WithdrawalLifecycleHandler",
    "WithdrawalQueryService",
    "WithdrawalStatisticsService",
    "WithdrawalHelpers",
]
