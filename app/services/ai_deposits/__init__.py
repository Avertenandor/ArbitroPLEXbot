"""
AI Deposits Management Service.

Provides comprehensive deposit management for AI assistant:
- View deposits (user, platform-wide)
- Create/modify deposits (TRUSTED ADMINS ONLY)
- Level management
- Pending deposits

SECURITY: Deposit modifications require TRUSTED_ADMIN access.

This package is split into modules:
- core.py: Base class and utilities
- queries.py: Read operations
- operations.py: Write operations (TRUSTED ADMIN only)
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from .operations import AIDepositsOperationsService
from .queries import AIDepositsQueriesService

__all__ = ["AIDepositsService"]


class AIDepositsService(
    AIDepositsQueriesService,
    AIDepositsOperationsService,
):
    """
    AI-powered deposits management service.

    Provides full deposit management for ARIA.
    ALL ADMINS are now trusted to manage deposits via ARIA.

    Combines query and operation capabilities:
    - Read operations (all admins)
    - Write operations (trusted admins only)
    """

    def __init__(
        self,
        session: AsyncSession,
        admin_data: dict[str, Any] | None = None,
    ):
        """
        Initialize AI Deposits Service.

        Args:
            session: Database session
            admin_data: Admin information (ID, username)
        """
        # Call parent __init__ from core (via queries or operations)
        super().__init__(session, admin_data)
