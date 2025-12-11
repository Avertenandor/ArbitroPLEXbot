"""Deposits tool handler for managing deposit operations.

This module provides the DepositsToolHandler class for handling deposit-related
tools including deposit creation, modification, cancellation, and retrieval operations.
"""

import logging
from typing import Any

from ..base import BaseToolHandler, HandlerContext
from ..validators import (
    validate_limit,
    validate_optional_string,
    validate_positive_decimal,
    validate_positive_int,
    validate_required_string,
    validate_user_identifier,
)

__all__ = ["DepositsToolHandler"]

logger = logging.getLogger(__name__)


class DepositsToolHandler(BaseToolHandler):
    """Handler for deposit management tools.

    This handler manages all deposit-related operations including:
    - Deposit configuration retrieval
    - User deposit listings
    - Pending deposit queries
    - Deposit details retrieval
    - Platform deposit statistics
    - Maximum deposit level changes
    - Manual deposit creation
    - Deposit ROI modifications
    - Deposit cancellation
    - Deposit confirmation

    Attributes:
        context: Handler context containing session, bot, and admin information.
        deposits_service: Service for executing deposit management operations.
    """

    def __init__(self, context: HandlerContext, deposits_service: Any) -> None:
        """Initialize the deposits tool handler.

        Args:
            context: Handler context containing necessary execution environment.
            deposits_service: Service instance for deposit management operations.
        """
        super().__init__(context)
        self.deposits_service = deposits_service

    def get_tool_names(self) -> set[str]:
        """Get the set of tool names that this handler can process.

        Returns:
            A set containing all deposit management tool names.
        """
        return {
            "get_deposit_levels_config",
            "get_user_deposits_list",
            "get_pending_deposits",
            "get_deposit_details",
            "get_platform_deposit_stats",
            "change_max_deposit_level",
            "create_manual_deposit",
            "modify_deposit_roi",
            "cancel_deposit",
            "confirm_deposit",
        }

    async def handle(self, tool_name: str, tool_input: dict, **kwargs) -> Any:
        """Handle the execution of a specific deposit management tool.

        Args:
            tool_name: Name of the tool to execute.
            tool_input: Dictionary containing input parameters for the tool.
            **kwargs: Additional keyword arguments for tool execution.

        Returns:
            The result of the tool execution.

        Raises:
            ValueError: If the tool name is unknown or input validation fails.
        """
        logger.info(
            f"Executing deposit tool '{tool_name}' for admin_id={self.context.admin_id}"
        )

        if tool_name == "get_deposit_levels_config":
            return await self._get_deposit_levels_config(tool_input)
        elif tool_name == "get_user_deposits_list":
            return await self._get_user_deposits_list(tool_input)
        elif tool_name == "get_pending_deposits":
            return await self._get_pending_deposits(tool_input)
        elif tool_name == "get_deposit_details":
            return await self._get_deposit_details(tool_input)
        elif tool_name == "get_platform_deposit_stats":
            return await self._get_platform_deposit_stats(tool_input)
        elif tool_name == "change_max_deposit_level":
            return await self._change_max_deposit_level(tool_input)
        elif tool_name == "create_manual_deposit":
            return await self._create_manual_deposit(tool_input)
        elif tool_name == "modify_deposit_roi":
            return await self._modify_deposit_roi(tool_input)
        elif tool_name == "cancel_deposit":
            return await self._cancel_deposit(tool_input)
        elif tool_name == "confirm_deposit":
            return await self._confirm_deposit(tool_input)
        else:
            error_msg = f"Unknown deposit tool: {tool_name}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    async def _get_deposit_levels_config(self, tool_input: dict) -> Any:
        """Get deposit levels configuration.

        Args:
            tool_input: Dictionary (no parameters required).

        Returns:
            Deposit levels configuration from the deposits service.
        """
        logger.debug("Getting deposit levels configuration")

        return await self.deposits_service.get_deposit_levels_config()

    async def _get_user_deposits_list(self, tool_input: dict) -> Any:
        """Get list of deposits for a specific user.

        Args:
            tool_input: Dictionary with keys:
                - user_identifier: User's Telegram ID or username (required)

        Returns:
            List of user deposits from the deposits service.

        Raises:
            ValueError: If user_identifier validation fails.
        """
        logger.debug("Getting user deposits list")

        user_identifier = validate_user_identifier(
            tool_input.get("user_identifier"),
            "user_identifier"
        )

        return await self.deposits_service.get_user_deposits_list(
            user_identifier=user_identifier
        )

    async def _get_pending_deposits(self, tool_input: dict) -> Any:
        """Get list of pending deposits.

        Args:
            tool_input: Dictionary with keys:
                - limit: Maximum number of results (optional, default: 20, max: 100)

        Returns:
            List of pending deposits from the deposits service.
        """
        logger.debug("Getting pending deposits")

        limit = validate_limit(
            tool_input.get("limit"),
            default=20,
            max_limit=100
        )

        return await self.deposits_service.get_pending_deposits(
            limit=limit
        )

    async def _get_deposit_details(self, tool_input: dict) -> Any:
        """Get detailed information about a specific deposit.

        Args:
            tool_input: Dictionary with keys:
                - deposit_id: ID of the deposit as positive integer (required)

        Returns:
            Deposit details from the deposits service.

        Raises:
            ValueError: If deposit_id validation fails.
        """
        logger.debug("Getting deposit details")

        deposit_id = validate_positive_int(
            tool_input.get("deposit_id"),
            "deposit_id"
        )

        return await self.deposits_service.get_deposit_details(
            deposit_id=deposit_id
        )

    async def _get_platform_deposit_stats(self, tool_input: dict) -> Any:
        """Get platform-wide deposit statistics.

        Args:
            tool_input: Dictionary (no parameters required).

        Returns:
            Platform deposit statistics from the deposits service.
        """
        logger.debug("Getting platform deposit statistics")

        return await self.deposits_service.get_platform_deposit_stats()

    async def _change_max_deposit_level(self, tool_input: dict) -> Any:
        """Change the maximum deposit level allowed on the platform.

        Args:
            tool_input: Dictionary with keys:
                - new_max: New maximum deposit level as positive integer (required, max: 10)

        Returns:
            Result from the deposits service.

        Raises:
            ValueError: If new_max validation fails.
        """
        logger.debug("Changing max deposit level")

        new_max = validate_positive_int(
            tool_input.get("new_max"),
            "new_max",
            max_value=10
        )

        logger.info(f"Changing max deposit level to: {new_max}")

        return await self.deposits_service.change_max_deposit_level(
            new_max=new_max
        )

    async def _create_manual_deposit(self, tool_input: dict) -> Any:
        """Create a manual deposit for a user.

        Args:
            tool_input: Dictionary with keys:
                - user_identifier: User's Telegram ID or username (required)
                - level: Deposit level as integer (required, range: 1-10)
                - amount: Deposit amount as positive decimal (required)
                - reason: Reason for manual deposit, max 500 chars (required)

        Returns:
            Result from the deposits service.

        Raises:
            ValueError: If validation fails for any input parameter.
        """
        logger.debug("Creating manual deposit")

        user_identifier = validate_user_identifier(
            tool_input.get("user_identifier"),
            "user_identifier"
        )
        level = validate_positive_int(
            tool_input.get("level"),
            "level",
            max_value=10
        )
        if level < 1:
            raise ValueError("level must be between 1 and 10")

        amount = validate_positive_decimal(
            tool_input.get("amount"),
            "amount"
        )
        reason = validate_required_string(
            tool_input.get("reason"),
            "reason",
            max_length=500
        )

        logger.info(
            f"Creating manual deposit: user={user_identifier}, level={level}, "
            f"amount={amount}, reason='{reason[:50]}...'"
        )

        return await self.deposits_service.create_manual_deposit(
            user_identifier=user_identifier,
            level=level,
            amount=amount,
            reason=reason
        )

    async def _modify_deposit_roi(self, tool_input: dict) -> Any:
        """Modify ROI parameters for an existing deposit.

        Args:
            tool_input: Dictionary with keys:
                - deposit_id: ID of the deposit as positive integer (required)
                - reason: Reason for ROI modification, max 500 chars (required)
                - new_roi_paid: New ROI paid amount as positive decimal (optional)
                - new_roi_cap: New ROI cap amount as positive decimal (optional)

        Returns:
            Result from the deposits service.

        Raises:
            ValueError: If validation fails for any input parameter.
        """
        logger.debug("Modifying deposit ROI")

        deposit_id = validate_positive_int(
            tool_input.get("deposit_id"),
            "deposit_id"
        )
        reason = validate_required_string(
            tool_input.get("reason"),
            "reason",
            max_length=500
        )

        new_roi_paid = None
        if tool_input.get("new_roi_paid") is not None:
            new_roi_paid = validate_positive_decimal(
                tool_input.get("new_roi_paid"),
                "new_roi_paid"
            )

        new_roi_cap = None
        if tool_input.get("new_roi_cap") is not None:
            new_roi_cap = validate_positive_decimal(
                tool_input.get("new_roi_cap"),
                "new_roi_cap"
            )

        logger.info(
            f"Modifying deposit ROI: deposit_id={deposit_id}, "
            f"new_roi_paid={new_roi_paid}, new_roi_cap={new_roi_cap}, "
            f"reason='{reason[:50]}...'"
        )

        return await self.deposits_service.modify_deposit_roi(
            deposit_id=deposit_id,
            reason=reason,
            new_roi_paid=new_roi_paid,
            new_roi_cap=new_roi_cap
        )

    async def _cancel_deposit(self, tool_input: dict) -> Any:
        """Cancel an existing deposit.

        Args:
            tool_input: Dictionary with keys:
                - deposit_id: ID of the deposit to cancel as positive integer (required)
                - reason: Reason for cancellation, max 500 chars (required)

        Returns:
            Result from the deposits service.

        Raises:
            ValueError: If validation fails for any input parameter.
        """
        logger.debug("Canceling deposit")

        deposit_id = validate_positive_int(
            tool_input.get("deposit_id"),
            "deposit_id"
        )
        reason = validate_required_string(
            tool_input.get("reason"),
            "reason",
            max_length=500
        )

        logger.info(
            f"Canceling deposit: deposit_id={deposit_id}, reason='{reason[:50]}...'"
        )

        return await self.deposits_service.cancel_deposit(
            deposit_id=deposit_id,
            reason=reason
        )

    async def _confirm_deposit(self, tool_input: dict) -> Any:
        """Confirm a pending deposit.

        Args:
            tool_input: Dictionary with keys:
                - deposit_id: ID of the deposit to confirm as positive integer (required)
                - reason: Optional reason for confirmation, max 500 chars (optional)

        Returns:
            Result from the deposits service.

        Raises:
            ValueError: If deposit_id validation fails.
        """
        logger.debug("Confirming deposit")

        deposit_id = validate_positive_int(
            tool_input.get("deposit_id"),
            "deposit_id"
        )
        reason = validate_optional_string(
            tool_input.get("reason"),
            "reason",
            max_length=500
        )

        logger.info(
            f"Confirming deposit: deposit_id={deposit_id}, reason={reason}"
        )

        return await self.deposits_service.confirm_deposit(
            deposit_id=deposit_id,
            reason=reason
        )
