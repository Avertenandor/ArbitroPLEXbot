"""
Withdrawal service - Main service facade.

This service acts as a facade that delegates to specialized modules
for better code organization and maintainability. All functionality
is preserved and backward compatibility is maintained.

Module structure:
- withdrawal/withdrawal_request_handler: Request creation and validation
- withdrawal/withdrawal_lifecycle_handler: Approval, rejection, cancellation
- withdrawal/withdrawal_query_service: Queries and history
- withdrawal/withdrawal_statistics_service: Statistics and reporting
- withdrawal/withdrawal_helpers: Utility functions
"""

from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.services.base_service import BaseService
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


class WithdrawalService(BaseService):
    """
    Withdrawal service for managing withdrawal requests.

    This is a facade that delegates to specialized modules for better
    code organization. All public methods maintain backward compatibility.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize withdrawal service and all sub-components."""
        super().__init__(session)

        # Initialize all specialized components
        self.request_handler = WithdrawalRequestHandler(session)
        self.lifecycle_handler = WithdrawalLifecycleHandler(session)
        self.query_service = WithdrawalQueryService(session)
        self.statistics_service = WithdrawalStatisticsService(session)
        self.helpers = WithdrawalHelpers(session)

    # ========================================================================
    # REQUEST HANDLING (delegates to WithdrawalRequestHandler)
    # ========================================================================

    async def get_min_withdrawal_amount(self) -> Decimal:
        """
        Get minimum withdrawal amount from global settings.

        Returns:
            Minimum withdrawal amount
        """
        return await self.request_handler.get_min_withdrawal_amount()

    async def request_withdrawal(
        self,
        user_id: int,
        amount: Decimal,
        available_balance: Decimal,
    ) -> tuple[Transaction | None, str | None, bool]:
        """
        Request withdrawal with balance deduction.

        Args:
            user_id: User ID
            amount: Withdrawal amount
            available_balance: User's available balance

        Returns:
            Tuple of (transaction, error_message, is_auto_approved)
        """
        return await self.request_handler.request_withdrawal(
            user_id, amount, available_balance
        )

    # ========================================================================
    # LIFECYCLE MANAGEMENT (delegates to WithdrawalLifecycleHandler)
    # ========================================================================

    async def cancel_withdrawal(
        self, transaction_id: int, user_id: int
    ) -> tuple[bool, str | None]:
        """
        Cancel withdrawal and RETURN BALANCE to user.

        Args:
            transaction_id: Transaction ID
            user_id: User ID (for authorization)

        Returns:
            Tuple of (success, error_message)
        """
        return await self.lifecycle_handler.cancel_withdrawal(
            transaction_id, user_id
        )

    async def approve_withdrawal(
        self,
        transaction_id: int,
        tx_hash: str,
        admin_id: int | None = None,
    ) -> tuple[bool, str | None]:
        """
        Approve withdrawal (admin only).

        R18-4: This method is called after dual control is completed
        (escrow approved by second admin) or for small withdrawals.

        Args:
            transaction_id: Transaction ID
            tx_hash: Blockchain transaction hash
            admin_id: Admin ID (for logging)

        Returns:
            Tuple of (success, error_message)
        """
        return await self.lifecycle_handler.approve_withdrawal(
            transaction_id, tx_hash, admin_id
        )

    async def approve_withdrawal_via_escrow(
        self,
        escrow_id: int,
        approver_admin_id: int,
        blockchain_service: Any,
    ) -> tuple[bool, str | None, str | None]:
        """
        Approve withdrawal via escrow (second admin).

        Args:
            escrow_id: Escrow ID
            approver_admin_id: Second admin ID
            blockchain_service: Blockchain service instance

        Returns:
            Tuple of (success, error_message, tx_hash)
        """
        return await self.lifecycle_handler.approve_withdrawal_via_escrow(
            escrow_id, approver_admin_id, blockchain_service
        )

    async def reject_withdrawal(
        self, transaction_id: int, reason: str | None = None
    ) -> tuple[bool, str | None]:
        """
        Reject withdrawal and RETURN BALANCE.

        Args:
            transaction_id: Transaction ID
            reason: Rejection reason (optional)

        Returns:
            Tuple of (success, error_message)
        """
        return await self.lifecycle_handler.reject_withdrawal(
            transaction_id, reason
        )

    # ========================================================================
    # QUERY OPERATIONS (delegates to WithdrawalQueryService)
    # ========================================================================

    async def get_pending_withdrawals(
        self,
    ) -> list[Transaction]:
        """
        Get pending withdrawals (for admin).

        Returns:
            List of pending withdrawal transactions
        """
        return await self.query_service.get_pending_withdrawals()

    async def get_user_withdrawals(
        self,
        user_id: int,
        page: int = 1,
        limit: int = 10,
    ) -> dict:
        """
        Get user withdrawal history.

        Args:
            user_id: User ID
            page: Page number (1-indexed)
            limit: Items per page

        Returns:
            Dict with withdrawals, total, page, pages
        """
        return await self.query_service.get_user_withdrawals(
            user_id, page, limit
        )

    async def get_withdrawal_by_id(
        self, transaction_id: int
    ) -> Transaction | None:
        """
        Get withdrawal by ID (admin only).

        Args:
            transaction_id: Transaction ID

        Returns:
            Transaction or None if not found
        """
        return await self.query_service.get_withdrawal_by_id(transaction_id)

    # ========================================================================
    # STATISTICS (delegates to WithdrawalStatisticsService)
    # ========================================================================

    async def get_platform_withdrawal_stats(self) -> dict:
        """
        Get platform-wide withdrawal statistics.

        Returns:
            Dictionary with withdrawal stats including:
            - total_confirmed: Total confirmed withdrawals count
            - total_confirmed_amount: Total amount of confirmed withdrawals
            - total_failed: Total failed withdrawals count
            - total_failed_amount: Total amount of failed withdrawals
            - by_user: List of users with their withdrawal amounts
        """
        return await self.statistics_service.get_platform_withdrawal_stats()

    async def get_detailed_withdrawals(
        self, page: int = 1, per_page: int = 5
    ) -> dict:
        """
        Get detailed withdrawal transactions with pagination.

        Args:
            page: Page number (1-based)
            per_page: Items per page

        Returns:
            Dictionary with withdrawals list and pagination info
        """
        return await self.statistics_service.get_detailed_withdrawals(
            page, per_page
        )

    # ========================================================================
    # HELPER METHODS (delegates to WithdrawalHelpers)
    # ========================================================================

    async def _check_daily_withdrawal_limit(
        self, user_id: int, requested_amount: Decimal
    ) -> dict:
        """
        Check if withdrawal exceeds daily limit (= daily ROI).

        Args:
            user_id: User ID
            requested_amount: Requested withdrawal amount

        Returns:
            Dict with exceeded, daily_roi, withdrawn_today, remaining
        """
        return await self.helpers.check_daily_withdrawal_limit(
            user_id, requested_amount
        )

    async def handle_successful_withdrawal_with_old_password(
        self, user_id: int
    ) -> None:
        """
        Handle successful withdrawal with old password.

        Args:
            user_id: User ID
        """
        return await self.helpers.handle_successful_withdrawal_with_old_password(
            user_id
        )
