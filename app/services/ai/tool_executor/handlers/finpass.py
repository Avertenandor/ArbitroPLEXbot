"""Finpass recovery tool handler for AI assistant.

This handler manages finpass recovery operations including listing requests,
viewing details, approving/rejecting requests, and viewing statistics.
"""

import logging
from typing import Any

from ..base import BaseToolHandler, HandlerContext


__all__ = ["FinpassToolHandler"]

logger = logging.getLogger(__name__)


class FinpassToolHandler(BaseToolHandler):
    """Handler for finpass recovery management tools.

    This handler provides tools for managing finpass recovery requests including:
    - Listing finpass recovery requests with optional limits
    - Viewing detailed request information
    - Approving finpass recovery requests
    - Rejecting finpass recovery requests
    - Viewing finpass recovery statistics

    Attributes:
        context: Handler context containing session, bot, and admin information.
        finpass_service: Service instance for finpass recovery operations.
    """

    def __init__(self, context: HandlerContext, finpass_service: Any) -> None:
        """Initialize the finpass tool handler.

        Args:
            context: Handler context containing session, bot, and admin information.
            finpass_service: Service instance for performing finpass recovery operations.
        """
        super().__init__(context)
        self.finpass_service = finpass_service

    def get_tool_names(self) -> set[str]:
        """Get the set of tool names that this handler can process.

        Returns:
            Set of tool names supported by this handler.
        """
        return {
            "get_finpass_requests",
            "get_finpass_request_details",
            "approve_finpass_request",
            "reject_finpass_request",
            "get_finpass_stats",
        }

    async def handle(self, tool_name: str, tool_input: dict, **kwargs) -> Any:
        """Handle the execution of a finpass recovery tool.

        Args:
            tool_name: Name of the tool to execute.
            tool_input: Dictionary containing input parameters for the tool.
            **kwargs: Additional keyword arguments.

        Returns:
            The result of the tool execution.

        Raises:
            ValueError: If the tool name is not recognized.
        """
        logger.info(
            f"Finpass tool execution: tool={tool_name} "
            f"admin_id={self.context.admin_id}"
        )

        if tool_name == "get_finpass_requests":
            return await self._get_finpass_requests(tool_input)
        elif tool_name == "get_finpass_request_details":
            return await self._get_finpass_request_details(tool_input)
        elif tool_name == "approve_finpass_request":
            return await self._approve_finpass_request(tool_input)
        elif tool_name == "reject_finpass_request":
            return await self._reject_finpass_request(tool_input)
        elif tool_name == "get_finpass_stats":
            return await self._get_finpass_stats(tool_input)
        else:
            error_msg = f"Unknown finpass tool: {tool_name}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    async def _get_finpass_requests(self, tool_input: dict) -> Any:
        """Get list of finpass recovery requests.

        Args:
            tool_input: Dictionary with optional 'limit' field (default 20).

        Returns:
            Result dictionary with finpass requests list.
        """
        limit = tool_input.get("limit", 20)

        logger.info(
            f"Getting finpass requests: limit={limit}, "
            f"admin_id={self.context.admin_id}"
        )

        result = await self.finpass_service.get_finpass_requests(limit=limit)

        logger.info(f"Finpass requests retrieved: count={result.get('total_count', 0)}")
        return result

    async def _get_finpass_request_details(self, tool_input: dict) -> Any:
        """Get detailed information about a specific finpass recovery request.

        Args:
            tool_input: Dictionary with required 'request_id' field.

        Returns:
            Result dictionary with request details.
        """
        request_id = tool_input.get("request_id")

        if not request_id:
            return {"success": False, "error": "request_id is required"}

        logger.info(
            f"Getting finpass request details: request_id={request_id}, "
            f"admin_id={self.context.admin_id}"
        )

        result = await self.finpass_service.get_finpass_request_details(
            request_id=request_id
        )

        logger.info(f"Finpass request details retrieved: request_id={request_id}")
        return result

    async def _approve_finpass_request(self, tool_input: dict) -> Any:
        """Approve a finpass recovery request.

        Args:
            tool_input: Dictionary with required 'request_id' field and
                       optional 'notes' field.

        Returns:
            Result dictionary with approval status.
        """
        request_id = tool_input.get("request_id")
        notes = tool_input.get("notes")

        if not request_id:
            return {"success": False, "error": "request_id is required"}

        logger.info(
            f"Approving finpass request: request_id={request_id}, "
            f"admin_id={self.context.admin_id}"
        )

        result = await self.finpass_service.approve_finpass_request(
            request_id=request_id,
            notes=notes,
        )

        if result.get("success"):
            logger.info(
                f"Finpass request approved successfully: request_id={request_id}, "
                f"admin_id={self.context.admin_id}"
            )
        else:
            logger.warning(
                f"Failed to approve finpass request: request_id={request_id}, "
                f"error={result.get('error')}"
            )

        return result

    async def _reject_finpass_request(self, tool_input: dict) -> Any:
        """Reject a finpass recovery request.

        Args:
            tool_input: Dictionary with required 'request_id' and 'reason' fields.

        Returns:
            Result dictionary with rejection status.
        """
        request_id = tool_input.get("request_id")
        reason = tool_input.get("reason")

        if not request_id:
            return {"success": False, "error": "request_id is required"}

        if not reason:
            return {"success": False, "error": "reason is required"}

        logger.info(
            f"Rejecting finpass request: request_id={request_id}, "
            f"admin_id={self.context.admin_id}"
        )

        result = await self.finpass_service.reject_finpass_request(
            request_id=request_id,
            reason=reason,
        )

        if result.get("success"):
            logger.info(
                f"Finpass request rejected successfully: request_id={request_id}, "
                f"admin_id={self.context.admin_id}"
            )
        else:
            logger.warning(
                f"Failed to reject finpass request: request_id={request_id}, "
                f"error={result.get('error')}"
            )

        return result

    async def _get_finpass_stats(self, tool_input: dict) -> Any:
        """Get finpass recovery statistics.

        Args:
            tool_input: Dictionary (no parameters required).

        Returns:
            Result dictionary with finpass statistics.
        """
        logger.info(
            f"Getting finpass statistics: admin_id={self.context.admin_id}"
        )

        result = await self.finpass_service.get_finpass_stats()

        logger.info("Finpass statistics retrieved successfully")
        return result
