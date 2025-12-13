"""
Withdrawal validation service.

Handles all validation logic for withdrawal requests.

This module serves as a facade, re-exporting classes from modular
components:
- withdrawal_validator_core: Main validation logic
- withdrawal_plex_checks: PLEX-specific checks
- withdrawal_security_checks: Security checks
"""

from app.services.withdrawal.withdrawal_validator_core import (
    ValidationResult,
    WithdrawalValidator,
)

__all__ = [
    "ValidationResult",
    "WithdrawalValidator",
]
