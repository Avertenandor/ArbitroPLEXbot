"""User management tool handler.

This module provides the UsersToolHandler class for managing user-related operations
in the AI assistant, including profile retrieval, search, balance management, and blocking.
"""

import logging
from typing import Any

from ..base import BaseToolHandler, HandlerContext
from ..validators import (
    validate_enum,
    validate_limit,
    validate_positive_decimal,
    validate_required_string,
    validate_user_identifier,
)

__all__ = ["UsersToolHandler"]

logger = logging.getLogger(__name__)


class UsersToolHandler(BaseToolHandler):
    """Handler for user management tools.

    This handler manages all user-related operations including:
    - User profile retrieval
    - User search
    - Balance management
    - User blocking/unblocking
    - Deposit tracking
    - User statistics

    Attributes:
        context: Handler context containing session, bot, and admin information.
        users_service: Service for executing user management operations.
    """

    def __init__(self, context: HandlerContext, users_service: Any) -> None:
        """Initialize the users tool handler.

        Args:
            context: Handler context containing necessary execution environment.
            users_service: Service instance for user management operations.
        """
        super().__init__(context)
        self.users_service = users_service

    def get_tool_names(self) -> set[str]:
        """Get the set of tool names that this handler can process.

        Returns:
            A set containing all user management tool names.
        """
        return {
            "get_user_profile",
            "search_users",
            "change_user_balance",
            "block_user",
            "unblock_user",
            "get_user_deposits",
            "get_users_stats",
        }

    async def handle(self, tool_name: str, tool_input: dict, **kwargs) -> Any:
        """Handle the execution of a specific user management tool.

        Args:
            tool_name: Name of the tool to execute.
            tool_input: Dictionary containing input parameters for the tool.
            **kwargs: Additional keyword arguments for tool execution.

        Returns:
            The result of the tool execution.

        Raises:
            ValueError: If the tool name is unknown or input validation fails.
        """
        logger.info(f"Executing user management tool: {tool_name}")

        if tool_name == "get_user_profile":
            return await self._get_user_profile(tool_input)
        elif tool_name == "search_users":
            return await self._search_users(tool_input)
        elif tool_name == "change_user_balance":
            return await self._change_user_balance(tool_input)
        elif tool_name == "block_user":
            return await self._block_user(tool_input)
        elif tool_name == "unblock_user":
            return await self._unblock_user(tool_input)
        elif tool_name == "get_user_deposits":
            return await self._get_user_deposits(tool_input)
        elif tool_name == "get_users_stats":
            return await self._get_users_stats(tool_input)
        else:
            raise ValueError(f"Unknown user management tool: {tool_name}")

    async def _get_user_profile(self, tool_input: dict) -> Any:
        """Get user profile information.

        Args:
            tool_input: Dictionary containing user_identifier.

        Returns:
            User profile information.
        """
        logger.debug("Getting user profile")

        user_identifier = validate_user_identifier(
            tool_input.get("user_identifier"),
            "user_identifier"
        )

        return await self.users_service.get_user_profile(
            user_identifier=user_identifier
        )

    async def _search_users(self, tool_input: dict) -> Any:
        """Search for users.

        Args:
            tool_input: Dictionary containing query and optional limit.

        Returns:
            List of matching users.
        """
        logger.debug("Searching users")

        query = validate_required_string(
            tool_input.get("query"),
            "query",
            max_length=100
        )
        limit = validate_limit(
            tool_input.get("limit"),
            default=20,
            max_limit=50
        )

        return await self.users_service.search_users(
            query=query,
            limit=limit
        )

    async def _change_user_balance(self, tool_input: dict) -> Any:
        """Change user balance.

        Args:
            tool_input: Dictionary containing user_identifier, amount, reason, and operation.

        Returns:
            Result of balance change operation.
        """
        logger.debug("Changing user balance")

        user_identifier = validate_user_identifier(
            tool_input.get("user_identifier"),
            "user_identifier"
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
        operation = validate_enum(
            tool_input.get("operation"),
            "operation",
            allowed_values={"add", "subtract", "set"}
        )

        return await self.users_service.change_user_balance(
            user_identifier=user_identifier,
            amount=amount,
            reason=reason,
            operation=operation
        )

    async def _block_user(self, tool_input: dict) -> Any:
        """Block a user.

        Args:
            tool_input: Dictionary containing user_identifier and reason.

        Returns:
            Result of block operation.
        """
        logger.debug("Blocking user")

        user_identifier = validate_user_identifier(
            tool_input.get("user_identifier"),
            "user_identifier"
        )
        reason = validate_required_string(
            tool_input.get("reason"),
            "reason",
            max_length=500
        )

        return await self.users_service.block_user(
            user_identifier=user_identifier,
            reason=reason
        )

    async def _unblock_user(self, tool_input: dict) -> Any:
        """Unblock a user.

        Args:
            tool_input: Dictionary containing user_identifier.

        Returns:
            Result of unblock operation.
        """
        logger.debug("Unblocking user")

        user_identifier = validate_user_identifier(
            tool_input.get("user_identifier"),
            "user_identifier"
        )

        return await self.users_service.unblock_user(
            user_identifier=user_identifier
        )

    async def _get_user_deposits(self, tool_input: dict) -> Any:
        """Get user deposits.

        Args:
            tool_input: Dictionary containing user_identifier.

        Returns:
            List of user deposits.
        """
        logger.debug("Getting user deposits")

        user_identifier = validate_user_identifier(
            tool_input.get("user_identifier"),
            "user_identifier"
        )

        return await self.users_service.get_user_deposits(
            user_identifier=user_identifier
        )

    async def _get_users_stats(self, tool_input: dict) -> Any:
        """Get users statistics.

        Args:
            tool_input: Dictionary (no parameters required).

        Returns:
            Users statistics.
        """
        logger.debug("Getting users statistics")

        return await self.users_service.get_users_stats()
