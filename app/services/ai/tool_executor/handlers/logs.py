"""Logs and activity monitoring tool handler.

This module provides the LogsToolHandler class for managing log and activity monitoring
operations in the AI assistant, including recent logs, admin activity tracking, and log search.
"""

import logging
from typing import Any

from ..base import BaseToolHandler, HandlerContext
from ..validators import (
    validate_limit,
    validate_optional_string,
    validate_required_string,
)

__all__ = ["LogsToolHandler"]

logger = logging.getLogger(__name__)


class LogsToolHandler(BaseToolHandler):
    """Handler for logs and activity monitoring tools.

    This handler manages all log-related operations including:
    - Recent system logs retrieval
    - Admin activity tracking
    - Log search with filters
    - Action type statistics

    Attributes:
        context: Handler context containing session, bot, and admin information.
        logs_service: Service for executing log management operations.
    """

    def __init__(self, context: HandlerContext, service: Any) -> None:
        """Initialize the logs tool handler.

        Args:
            context: Handler context containing necessary execution environment.
            service: Service instance for log management operations.
        """
        super().__init__(context)
        self.logs_service = service

    def get_tool_names(self) -> set[str]:
        """Get the set of tool names that this handler can process.

        Returns:
            A set containing all log management tool names.
        """
        return {
            "get_recent_logs",
            "get_admin_activity",
            "search_logs",
            "get_action_types_stats",
        }

    async def handle(self, tool_name: str, tool_input: dict, **kwargs) -> Any:
        """Handle the execution of a specific log management tool.

        Args:
            tool_name: Name of the tool to execute.
            tool_input: Dictionary containing input parameters for the tool.
            **kwargs: Additional keyword arguments for tool execution.

        Returns:
            The result of the tool execution.

        Raises:
            ValueError: If the tool name is unknown or input validation fails.
        """
        logger.info(f"Executing log management tool: {tool_name}")

        if tool_name == "get_recent_logs":
            return await self._get_recent_logs(tool_input)
        elif tool_name == "get_admin_activity":
            return await self._get_admin_activity(tool_input)
        elif tool_name == "search_logs":
            return await self._search_logs(tool_input)
        elif tool_name == "get_action_types_stats":
            return await self._get_action_types_stats(tool_input)
        else:
            raise ValueError(f"Unknown log management tool: {tool_name}")

    async def _get_recent_logs(self, tool_input: dict) -> Any:
        """Get recent system logs.

        Args:
            tool_input: Dictionary containing optional limit and action_type.

        Returns:
            List of recent log entries.
        """
        logger.debug("Getting recent logs")

        limit = validate_limit(
            tool_input.get("limit"),
            default=30,
            max_limit=100
        )
        action_type = validate_optional_string(
            tool_input.get("action_type"),
            "action_type",
            max_length=100
        )

        return await self.logs_service.get_recent_logs(
            limit=limit,
            action_type=action_type
        )

    async def _get_admin_activity(self, tool_input: dict) -> Any:
        """Get activity logs for a specific admin.

        Args:
            tool_input: Dictionary containing admin_identifier and optional limit.

        Returns:
            List of activity logs for the specified admin.
        """
        logger.debug("Getting admin activity")

        admin_identifier = validate_required_string(
            tool_input.get("admin_identifier"),
            "admin_identifier",
            max_length=100
        )
        limit = validate_limit(
            tool_input.get("limit"),
            default=30,
            max_limit=100
        )

        return await self.logs_service.get_admin_activity(
            admin_identifier=admin_identifier,
            limit=limit
        )

    async def _search_logs(self, tool_input: dict) -> Any:
        """Search logs with optional filters.

        Args:
            tool_input: Dictionary containing optional user_id, action_type, and limit.

        Returns:
            List of matching log entries.
        """
        logger.debug("Searching logs")

        user_id = validate_optional_string(
            tool_input.get("user_id"),
            "user_id",
            max_length=100
        )
        action_type = validate_optional_string(
            tool_input.get("action_type"),
            "action_type",
            max_length=100
        )
        limit = validate_limit(
            tool_input.get("limit"),
            default=30,
            max_limit=100
        )

        return await self.logs_service.search_logs(
            user_id=user_id,
            action_type=action_type,
            limit=limit
        )

    async def _get_action_types_stats(self, tool_input: dict) -> Any:
        """Get statistics about different action types in logs.

        Args:
            tool_input: Dictionary (no parameters required).

        Returns:
            Statistics about action types including counts and frequencies.
        """
        logger.debug("Getting action types statistics")

        return await self.logs_service.get_action_types_stats()
