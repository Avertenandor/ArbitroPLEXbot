"""Blacklist management tool handler.

This module provides the BlacklistToolHandler class for managing blacklist-related operations
in the AI assistant, including retrieving, checking, adding, and removing blacklist entries.
"""

import logging
from typing import Any

from ..base import BaseToolHandler, HandlerContext
from ..validators import (
    validate_enum,
    validate_limit,
    validate_required_string,
)

__all__ = ["BlacklistToolHandler"]

logger = logging.getLogger(__name__)


class BlacklistToolHandler(BaseToolHandler):
    """Handler for blacklist management tools.

    This handler manages all blacklist-related operations including:
    - Retrieving blacklist entries
    - Checking if an identifier is blacklisted
    - Adding entries to the blacklist
    - Removing entries from the blacklist

    Attributes:
        context: Handler context containing session, bot, and admin information.
        blacklist_service: Service for executing blacklist management operations.
    """

    def __init__(self, context: HandlerContext, blacklist_service: Any) -> None:
        """Initialize the blacklist tool handler.

        Args:
            context: Handler context containing necessary execution environment.
            blacklist_service: Service instance for blacklist management operations.
        """
        super().__init__(context)
        self.blacklist_service = blacklist_service

    def get_tool_names(self) -> set[str]:
        """Get the set of tool names that this handler can process.

        Returns:
            A set containing all blacklist management tool names.
        """
        return {
            "get_blacklist",
            "check_blacklist",
            "add_to_blacklist",
            "remove_from_blacklist",
        }

    async def handle(self, tool_name: str, tool_input: dict, **kwargs) -> Any:
        """Handle the execution of a specific blacklist management tool.

        Args:
            tool_name: Name of the tool to execute.
            tool_input: Dictionary containing input parameters for the tool.
            **kwargs: Additional keyword arguments for tool execution.

        Returns:
            The result of the tool execution.

        Raises:
            ValueError: If the tool name is unknown or input validation fails.
        """
        logger.info(f"Executing blacklist management tool: {tool_name}")

        if tool_name == "get_blacklist":
            return await self._get_blacklist(tool_input)
        elif tool_name == "check_blacklist":
            return await self._check_blacklist(tool_input)
        elif tool_name == "add_to_blacklist":
            return await self._add_to_blacklist(tool_input)
        elif tool_name == "remove_from_blacklist":
            return await self._remove_from_blacklist(tool_input)
        else:
            raise ValueError(f"Unknown blacklist management tool: {tool_name}")

    async def _get_blacklist(self, tool_input: dict) -> Any:
        """Get blacklist entries.

        Args:
            tool_input: Dictionary containing optional limit parameter.

        Returns:
            List of blacklist entries.
        """
        logger.debug("Getting blacklist entries")

        limit = validate_limit(
            tool_input.get("limit"),
            default=50,
            max_limit=100
        )

        return await self.blacklist_service.get_blacklist(
            limit=limit
        )

    async def _check_blacklist(self, tool_input: dict) -> Any:
        """Check if an identifier is blacklisted.

        Args:
            tool_input: Dictionary containing identifier parameter.

        Returns:
            Blacklist status information for the identifier.
        """
        logger.debug("Checking blacklist status")

        identifier = validate_required_string(
            tool_input.get("identifier"),
            "identifier",
            max_length=200
        )

        return await self.blacklist_service.check_blacklist(
            identifier=identifier
        )

    async def _add_to_blacklist(self, tool_input: dict) -> Any:
        """Add an identifier to the blacklist.

        Args:
            tool_input: Dictionary containing identifier, reason, and optional action_type.

        Returns:
            Result of the add operation.
        """
        logger.debug("Adding to blacklist")

        identifier = validate_required_string(
            tool_input.get("identifier"),
            "identifier",
            max_length=200
        )
        reason = validate_required_string(
            tool_input.get("reason"),
            "reason",
            max_length=500
        )

        # Validate action_type if provided, otherwise use default
        action_type_value = tool_input.get("action_type")
        if action_type_value is None:
            action_type = "pre_block"
        else:
            action_type = validate_enum(
                action_type_value,
                "action_type",
                allowed_values={"pre_block", "block", "monitor"}
            )

        return await self.blacklist_service.add_to_blacklist(
            identifier=identifier,
            reason=reason,
            action_type=action_type
        )

    async def _remove_from_blacklist(self, tool_input: dict) -> Any:
        """Remove an identifier from the blacklist.

        Args:
            tool_input: Dictionary containing identifier and reason.

        Returns:
            Result of the remove operation.
        """
        logger.debug("Removing from blacklist")

        identifier = validate_required_string(
            tool_input.get("identifier"),
            "identifier",
            max_length=200
        )
        reason = validate_required_string(
            tool_input.get("reason"),
            "reason",
            max_length=500
        )

        return await self.blacklist_service.remove_from_blacklist(
            identifier=identifier,
            reason=reason
        )
