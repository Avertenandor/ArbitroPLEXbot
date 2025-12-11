"""Bonus tool handler for managing bonus operations.

This module provides the BonusToolHandler class for handling bonus-related
tools including granting bonuses, retrieving user bonuses, and canceling bonuses.
"""

import logging
from typing import Any

from ..base import BaseToolHandler, HandlerContext
from ..validators import (
    validate_positive_decimal,
    validate_positive_int,
    validate_required_string,
    validate_user_identifier,
)

__all__ = ["BonusToolHandler"]

logger = logging.getLogger(__name__)


class BonusToolHandler(BaseToolHandler):
    """Handler for bonus-related tools.

    This handler manages all bonus operations including granting bonuses to users,
    retrieving bonus history, and canceling bonuses. It validates inputs and
    delegates to the bonus service for actual operations.

    Attributes:
        context: The handler context containing session, bot, and admin information.
        bonus_service: Service instance for performing bonus operations.
    """

    def __init__(self, context: HandlerContext, bonus_service: Any) -> None:
        """Initialize the bonus tool handler.

        Args:
            context: Handler context containing necessary execution environment.
            bonus_service: Service instance for bonus operations.
        """
        super().__init__(context)
        self.bonus_service = bonus_service

    def get_tool_names(self) -> set[str]:
        """Get the set of tool names that this handler can process.

        Returns:
            A set containing "grant_bonus", "get_user_bonuses", and "cancel_bonus".
        """
        return {"grant_bonus", "get_user_bonuses", "cancel_bonus"}

    async def handle(self, tool_name: str, tool_input: dict, **kwargs) -> Any:
        """Handle the execution of a bonus tool.

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
            f"Executing bonus tool '{tool_name}' for admin_id={self.context.admin_id}"
        )

        if tool_name == "grant_bonus":
            return await self._grant_bonus(tool_input)
        elif tool_name == "get_user_bonuses":
            return await self._get_user_bonuses(tool_input)
        elif tool_name == "cancel_bonus":
            return await self._cancel_bonus(tool_input)
        else:
            error_msg = f"Unknown bonus tool: {tool_name}"
            logger.error(error_msg)
            return {"error": error_msg}

    async def _grant_bonus(self, tool_input: dict) -> Any:
        """Grant a bonus to a user.

        Args:
            tool_input: Dictionary with keys:
                - user_identifier: User's Telegram ID or username (required)
                - amount: Bonus amount as positive decimal (required)
                - reason: Reason for granting bonus, max 500 chars (required)

        Returns:
            Result from the bonus service.

        Raises:
            ValueError: If validation fails for any input parameter.
        """
        user_identifier = validate_user_identifier(
            tool_input.get("user_identifier")
        )
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
            f"Granting bonus: user={user_identifier}, amount={amount}, "
            f"reason='{reason[:50]}...'"
        )

        return await self.bonus_service.grant_bonus(
            user_identifier=user_identifier,
            amount=amount,
            reason=reason,
        )

    async def _get_user_bonuses(self, tool_input: dict) -> Any:
        """Get bonuses for a specific user.

        Args:
            tool_input: Dictionary with keys:
                - user_identifier: User's Telegram ID or username (required)
                - active_only: Boolean to filter only active bonuses (optional, default: False)

        Returns:
            List of user bonuses from the bonus service.

        Raises:
            ValueError: If user_identifier validation fails.
        """
        user_identifier = validate_user_identifier(
            tool_input.get("user_identifier")
        )
        active_only = bool(tool_input.get("active_only", False))

        logger.info(
            f"Retrieving bonuses: user={user_identifier}, active_only={active_only}"
        )

        return await self.bonus_service.get_user_bonuses(
            user_identifier=user_identifier,
            active_only=active_only,
        )

    async def _cancel_bonus(self, tool_input: dict) -> Any:
        """Cancel an existing bonus.

        Args:
            tool_input: Dictionary with keys:
                - bonus_id: ID of the bonus to cancel as positive integer (required)
                - reason: Reason for cancellation, max 500 chars (required)

        Returns:
            Result from the bonus service.

        Raises:
            ValueError: If validation fails for any input parameter.
        """
        bonus_id = validate_positive_int(
            tool_input.get("bonus_id"),
            "bonus_id"
        )
        reason = validate_required_string(
            tool_input.get("reason"),
            "reason",
            max_length=500
        )

        logger.info(
            f"Canceling bonus: bonus_id={bonus_id}, reason='{reason[:50]}...'"
        )

        return await self.bonus_service.cancel_bonus(
            bonus_id=bonus_id,
            reason=reason,
        )
