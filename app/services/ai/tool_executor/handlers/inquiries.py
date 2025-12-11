"""Inquiries tool handler for managing user inquiries.

This module provides the InquiriesToolHandler class that manages all inquiry-related
tools for the AI assistant, including listing, viewing, taking, replying to, and
closing user inquiries.
"""

import logging
from typing import Any

from ..base import BaseToolHandler, HandlerContext


__all__ = ["InquiriesToolHandler"]


logger = logging.getLogger(__name__)


class InquiriesToolHandler(BaseToolHandler):
    """Handler for inquiry management tools.

    This handler manages all inquiry-related operations including:
    - Getting list of inquiries
    - Getting inquiry details
    - Taking inquiries
    - Replying to inquiries
    - Closing inquiries

    Attributes:
        context: Handler context containing session, bot, and admin information.
        inquiries_service: Service instance for inquiry operations.
    """

    def __init__(
        self,
        context: HandlerContext,
        inquiries_service: Any,
    ) -> None:
        """Initialize the inquiries tool handler.

        Args:
            context: Handler context containing necessary execution environment.
            inquiries_service: Service instance for managing inquiries.
        """
        super().__init__(context)
        self.inquiries_service = inquiries_service

    def get_tool_names(self) -> set[str]:
        """Get the set of inquiry tool names that this handler can process.

        Returns:
            A set containing the 5 inquiry tool names.
        """
        return {
            "get_inquiries_list",
            "get_inquiry_details",
            "take_inquiry",
            "reply_to_inquiry",
            "close_inquiry",
        }

    async def handle(self, tool_name: str, tool_input: dict, **kwargs) -> Any:
        """Handle the execution of a specific inquiry tool.

        Args:
            tool_name: Name of the tool to execute.
            tool_input: Dictionary containing input parameters for the tool.
            **kwargs: Additional keyword arguments for tool execution.

        Returns:
            The result of the tool execution.

        Raises:
            ValueError: If the tool name is not recognized.
        """
        if tool_name == "get_inquiries_list":
            return await self._get_inquiries_list(tool_input)
        elif tool_name == "get_inquiry_details":
            return await self._get_inquiry_details(tool_input)
        elif tool_name == "take_inquiry":
            return await self._take_inquiry(tool_input)
        elif tool_name == "reply_to_inquiry":
            return await self._reply_to_inquiry(tool_input)
        elif tool_name == "close_inquiry":
            return await self._close_inquiry(tool_input)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def _get_inquiries_list(self, tool_input: dict) -> dict[str, Any]:
        """Get list of user inquiries with optional status filter.

        Args:
            tool_input: Dictionary containing:
                - status (optional): Filter by status (new, in_progress, closed)
                - limit (optional): Maximum number of inquiries to return (default 20)

        Returns:
            Result dictionary from the inquiries service.
        """
        status = tool_input.get("status")
        limit = tool_input.get("limit", 20)

        logger.info(
            f"Getting inquiries list: status={status}, limit={limit}, "
            f"admin_id={self.context.admin_id}"
        )

        result = await self.inquiries_service.get_inquiries_list(
            status=status,
            limit=limit,
        )

        logger.info(
            f"Inquiries list retrieved: success={result.get('success')}, "
            f"count={result.get('total_count', 0)}"
        )

        return result

    async def _get_inquiry_details(self, tool_input: dict) -> dict[str, Any]:
        """Get detailed information about a specific inquiry.

        Args:
            tool_input: Dictionary containing:
                - inquiry_id (required): ID of the inquiry to retrieve

        Returns:
            Result dictionary from the inquiries service.
        """
        inquiry_id = tool_input.get("inquiry_id")

        if not inquiry_id:
            logger.warning("get_inquiry_details called without inquiry_id")
            return {
                "success": False,
                "error": "❌ inquiry_id is required"
            }

        logger.info(
            f"Getting inquiry details: inquiry_id={inquiry_id}, "
            f"admin_id={self.context.admin_id}"
        )

        result = await self.inquiries_service.get_inquiry_details(
            inquiry_id=inquiry_id,
        )

        logger.info(
            f"Inquiry details retrieved: inquiry_id={inquiry_id}, "
            f"success={result.get('success')}"
        )

        return result

    async def _take_inquiry(self, tool_input: dict) -> dict[str, Any]:
        """Take inquiry for processing (assign to current admin).

        Args:
            tool_input: Dictionary containing:
                - inquiry_id (required): ID of the inquiry to take

        Returns:
            Result dictionary from the inquiries service.
        """
        inquiry_id = tool_input.get("inquiry_id")

        if not inquiry_id:
            logger.warning("take_inquiry called without inquiry_id")
            return {
                "success": False,
                "error": "❌ inquiry_id is required"
            }

        logger.info(
            f"Taking inquiry: inquiry_id={inquiry_id}, "
            f"admin_id={self.context.admin_id}"
        )

        result = await self.inquiries_service.take_inquiry(
            inquiry_id=inquiry_id,
        )

        logger.info(
            f"Inquiry take result: inquiry_id={inquiry_id}, "
            f"success={result.get('success')}"
        )

        return result

    async def _reply_to_inquiry(self, tool_input: dict) -> dict[str, Any]:
        """Send reply to user's inquiry.

        Args:
            tool_input: Dictionary containing:
                - inquiry_id (required): ID of the inquiry to reply to
                - message (required): Message text to send to the user

        Returns:
            Result dictionary from the inquiries service.
        """
        inquiry_id = tool_input.get("inquiry_id")
        message = tool_input.get("message")

        if not inquiry_id:
            logger.warning("reply_to_inquiry called without inquiry_id")
            return {
                "success": False,
                "error": "❌ inquiry_id is required"
            }

        if not message:
            logger.warning("reply_to_inquiry called without message")
            return {
                "success": False,
                "error": "❌ message is required"
            }

        logger.info(
            f"Replying to inquiry: inquiry_id={inquiry_id}, "
            f"admin_id={self.context.admin_id}, "
            f"message_length={len(message)}"
        )

        # Note: reply_to_inquiry needs the bot instance from context
        result = await self.inquiries_service.reply_to_inquiry(
            inquiry_id=inquiry_id,
            message=message,
            bot=self.context.bot,
        )

        logger.info(
            f"Reply result: inquiry_id={inquiry_id}, "
            f"success={result.get('success')}"
        )

        return result

    async def _close_inquiry(self, tool_input: dict) -> dict[str, Any]:
        """Close an inquiry.

        Args:
            tool_input: Dictionary containing:
                - inquiry_id (required): ID of the inquiry to close
                - reason (optional): Reason for closing the inquiry

        Returns:
            Result dictionary from the inquiries service.
        """
        inquiry_id = tool_input.get("inquiry_id")
        reason = tool_input.get("reason")

        if not inquiry_id:
            logger.warning("close_inquiry called without inquiry_id")
            return {
                "success": False,
                "error": "❌ inquiry_id is required"
            }

        logger.info(
            f"Closing inquiry: inquiry_id={inquiry_id}, "
            f"admin_id={self.context.admin_id}, "
            f"has_reason={bool(reason)}"
        )

        result = await self.inquiries_service.close_inquiry(
            inquiry_id=inquiry_id,
            reason=reason,
        )

        logger.info(
            f"Inquiry close result: inquiry_id={inquiry_id}, "
            f"success={result.get('success')}"
        )

        return result
