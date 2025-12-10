"""
Deposit validation service - backward compatibility module.

DEPRECATED: This module is kept for backward compatibility only.
Use app.services.deposit.validation_service instead.

All imports are re-exported from the new modular structure:
- app.services.deposit.validation_service - Main validation service
- app.services.deposit.constants - DEPOSIT_LEVELS and PARTNER_REQUIREMENTS
- app.services.deposit.validation - Individual validators
"""

# Re-export for backward compatibility
from app.services.deposit import DEPOSIT_LEVELS, PARTNER_REQUIREMENTS
from app.services.deposit.validation_service import DepositValidationService


__all__ = [
    "DepositValidationService",
    "DEPOSIT_LEVELS",
    "PARTNER_REQUIREMENTS",
]
