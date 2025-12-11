"""Withdrawals tool handler for managing withdrawal operations.

This module provides the WithdrawalsToolHandler class for handling withdrawal-related
tools including listing pending withdrawals, viewing details, approving, rejecting,
and retrieving statistics.
"""

import logging
from typing import Any

from ..base import BaseToolHandler, HandlerContext
from ..validators import (
    validate_limit,
    validate_optional_string,
    validate_positive_int,
    validate_required_string,
)

__all__ = ["WithdrawalsToolHandler"]

logger = logging.getLogger(__name__)


class WithdrawalsToolHandler(BaseToolHandler):
    """Handler for withdrawal-related tools.

    This handler manages all withdrawal operations including listing pending withdrawals,
    retrieving withdrawal details, approving and rejecting withdrawals, and fetching
    withdrawal statistics. It validates inputs and delegates to the withdrawals service
    for actual operations.

    Attributes:
        context: The handler context containing session, bot, and admin information.
        withdrawals_service: Service instance for performing withdrawal operations.
    """

    def __init__(self, context: HandlerContext, withdrawals_service: Any) -> None:
        """Initialize the withdrawals tool handler.

        Args:
            context: Handler context containing necessary execution environment.
            withdrawals_service: Service instance for withdrawal operations.
        """
        super().__init__(context)
        self.withdrawals_service = withdrawals_service

    def get_tool_names(self) -> set[str]:
        """Get the set of tool names that this handler can process.

        Returns:
            A set containing all withdrawal tool names.
        """
        return {
            "get_pending_withdrawals",
            "get_withdrawal_details",
            "approve_withdrawal",
            "reject_withdrawal",
            "get_withdrawals_statistics",
        }

    async def handle(self, tool_name: str, tool_input: dict, **kwargs) -> Any:
        """Handle the execution of a withdrawal tool.

        Args:
            tool_name: Name of the tool to execute.
            tool_input: Dictionary containing input parameters for the tool.
            **kwargs: Additional keyword arguments for tool execution.

        Returns:
            The result of the tool execution.

        Raises:
            ValueError: If input validation fails.
        """
        logger.info(
            f"Executing withdrawal tool '{tool_name}' for admin_id={self.context.admin_id}"
        )

        if tool_name == "get_pending_withdrawals":
            return await self._get_pending_withdrawals(tool_input)
        elif tool_name == "get_withdrawal_details":
            return await self._get_withdrawal_details(tool_input)
        elif tool_name == "approve_withdrawal":
            return await self._approve_withdrawal(tool_input)
        elif tool_name == "reject_withdrawal":
            return await self._reject_withdrawal(tool_input)
        elif tool_name == "get_withdrawals_statistics":
            return await self._get_withdrawals_statistics(tool_input)
        else:
            error_msg = f"Unknown withdrawal tool: {tool_name}"
            logger.error(error_msg)
            return {"error": error_msg}

    async def _get_pending_withdrawals(self, tool_input: dict) -> Any:
        """Get list of pending withdrawals.

        Args:
            tool_input: Dictionary with optional keys:
                - limit: Maximum number of withdrawals to retrieve (default: 20, max: 100)

        Returns:
            Result from the withdrawals service containing list of pending withdrawals.
        """
        limit = validate_limit(
            tool_input.get("limit"),
            default=20,
            max_limit=100
        )

        logger.info(
            f"Retrieving pending withdrawals: limit={limit}, "
            f"admin_id={self.context.admin_id}"
        )

        return await self.withdrawals_service.get_pending_withdrawals(limit=limit)

    async def _get_withdrawal_details(self, tool_input: dict) -> Any:
        """Get detailed information about a specific withdrawal.

        Args:
            tool_input: Dictionary with keys:
                - withdrawal_id: ID of the withdrawal as positive integer (required)

        Returns:
            Result from the withdrawals service containing withdrawal details.

        Raises:
            ValueError: If withdrawal_id validation fails.
        """
        withdrawal_id = validate_positive_int(
            tool_input.get("withdrawal_id"),
            "withdrawal_id"
        )

        logger.info(
            f"Retrieving withdrawal details: withdrawal_id={withdrawal_id}, "
            f"admin_id={self.context.admin_id}"
        )

        return await self.withdrawals_service.get_withdrawal_details(
            withdrawal_id=withdrawal_id
        )

    async def _approve_withdrawal(self, tool_input: dict) -> Any:
        """Approve a pending withdrawal.

        Args:
            tool_input: Dictionary with keys:
                - withdrawal_id: ID of the withdrawal as positive integer (required)
                - tx_hash: Transaction hash, max 100 chars (optional)

        Returns:
            Result from the withdrawals service.

        Raises:
            ValueError: If validation fails for any input parameter.
        """
        withdrawal_id = validate_positive_int(
            tool_input.get("withdrawal_id"),
            "withdrawal_id"
        )
        tx_hash = validate_optional_string(
            tool_input.get("tx_hash"),
            "tx_hash",
            max_length=100
        )

        logger.info(
            f"Approving withdrawal: withdrawal_id={withdrawal_id}, "
            f"has_tx_hash={tx_hash is not None}, admin_id={self.context.admin_id}"
        )

        return await self.withdrawals_service.approve_withdrawal(
            withdrawal_id=withdrawal_id,
            tx_hash=tx_hash,
        )

    async def _reject_withdrawal(self, tool_input: dict) -> Any:
        """Reject a pending withdrawal.

        Args:
            tool_input: Dictionary with keys:
                - withdrawal_id: ID of the withdrawal as positive integer (required)
                - reason: Reason for rejection, max 500 chars (required)

        Returns:
            Result from the withdrawals service.

        Raises:
            ValueError: If validation fails for any input parameter.
        """
        withdrawal_id = validate_positive_int(
            tool_input.get("withdrawal_id"),
            "withdrawal_id"
        )
        reason = validate_required_string(
            tool_input.get("reason"),
            "reason",
            max_length=500
        )

        logger.info(
            f"Rejecting withdrawal: withdrawal_id={withdrawal_id}, "
            f"reason='{reason[:50]}...', admin_id={self.context.admin_id}"
        )

        return await self.withdrawals_service.reject_withdrawal(
            withdrawal_id=withdrawal_id,
            reason=reason,
        )

    async def _get_withdrawals_statistics(self, tool_input: dict) -> Any:
        """Get withdrawal statistics.

        Args:
            tool_input: Dictionary (no parameters required for this tool).

        Returns:
            Result from the withdrawals service containing withdrawal statistics.
        """
        logger.info(
            f"Retrieving withdrawal statistics: admin_id={self.context.admin_id}"
        )

        return await self.withdrawals_service.get_withdrawals_statistics()
