"""
AI Deposits Management Service - Compatibility Module.

DEPRECATED: This file is maintained for backward compatibility.
The service has been refactored into app/services/ai_deposits/ package.

New structure:
- app/services/ai_deposits/core.py: Base class and utilities
- app/services/ai_deposits/queries.py: Read operations
- app/services/ai_deposits/operations.py: Write operations
- app/services/ai_deposits/__init__.py: Combined service

All functionality is preserved. Import from this module continues
to work as before.
"""

from app.services.ai_deposits import AIDepositsService

__all__ = ["AIDepositsService"]
