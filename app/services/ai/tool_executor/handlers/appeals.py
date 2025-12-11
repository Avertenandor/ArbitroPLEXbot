"""Appeals tool handler for AI assistant.

This handler manages appeal-related operations including listing appeals,
viewing details, taking appeals for review, resolving them, and replying to users.
"""

import logging
from typing import Any

from ..base import BaseToolHandler, HandlerContext


__all__ = ["AppealsToolHandler"]

logger = logging.getLogger(__name__)


class AppealsToolHandler(BaseToolHandler):
    """Handler for appeal management tools.

    This handler provides tools for managing user appeals including:
    - Listing appeals with optional status filtering
    - Viewing detailed appeal information
    - Taking appeals for review
    - Resolving appeals (approve/reject)
    - Replying to appeal submitters

    Attributes:
        context: Handler context containing session, bot, and admin information.
        appeals_service: Service instance for appeal operations.
    """

    def __init__(self, context: HandlerContext, appeals_service: Any) -> None:
        """Initialize the appeals tool handler.

        Args:
            context: Handler context containing session, bot, and admin information.
            appeals_service: Service instance for performing appeal operations.
        """
        super().__init__(context)
        self.appeals_service = appeals_service

    def get_tool_names(self) -> set[str]:
        """Get the set of tool names that this handler can process.

        Returns:
            Set of tool names supported by this handler.
        """
        return {
            "get_appeals_list",
            "get_appeal_details",
            "take_appeal",
            "resolve_appeal",
            "reply_to_appeal",
        }

    async def handle(self, tool_name: str, tool_input: dict, **kwargs) -> Any:
        """Handle the execution of an appeals tool.

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
            f"Appeals tool execution: tool={tool_name} "
            f"admin_id={self.context.admin_id}"
        )

        if tool_name == "get_appeals_list":
            return await self._get_appeals_list(tool_input)
        elif tool_name == "get_appeal_details":
            return await self._get_appeal_details(tool_input)
        elif tool_name == "take_appeal":
            return await self._take_appeal(tool_input)
        elif tool_name == "resolve_appeal":
            return await self._resolve_appeal(tool_input)
        elif tool_name == "reply_to_appeal":
            return await self._reply_to_appeal(tool_input)
        else:
            error_msg = f"Unknown appeals tool: {tool_name}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    async def _get_appeals_list(self, tool_input: dict) -> Any:
        """Get list of appeals with optional status filter.

        Args:
            tool_input: Dictionary with optional 'status' and 'limit' fields.

        Returns:
            Result dictionary with appeals list.
        """
        status = tool_input.get("status")
        limit = tool_input.get("limit", 20)

        logger.info(
            f"Getting appeals list: status={status}, limit={limit}, "
            f"admin_id={self.context.admin_id}"
        )

        result = await self.appeals_service.get_appeals_list(
            status=status,
            limit=limit,
        )

        logger.info(f"Appeals list retrieved: count={result.get('total_count', 0)}")
        return result

    async def _get_appeal_details(self, tool_input: dict) -> Any:
        """Get detailed information about a specific appeal.

        Args:
            tool_input: Dictionary with required 'appeal_id' field.

        Returns:
            Result dictionary with appeal details.
        """
        appeal_id = tool_input.get("appeal_id")

        if not appeal_id:
            return {"success": False, "error": "appeal_id is required"}

        logger.info(
            f"Getting appeal details: appeal_id={appeal_id}, "
            f"admin_id={self.context.admin_id}"
        )

        result = await self.appeals_service.get_appeal_details(appeal_id=appeal_id)

        logger.info(f"Appeal details retrieved: appeal_id={appeal_id}")
        return result

    async def _take_appeal(self, tool_input: dict) -> Any:
        """Take an appeal for review.

        Changes the appeal status to 'under_review' and assigns it to the admin.

        Args:
            tool_input: Dictionary with required 'appeal_id' field.

        Returns:
            Result dictionary with success status.
        """
        appeal_id = tool_input.get("appeal_id")

        if not appeal_id:
            return {"success": False, "error": "appeal_id is required"}

        logger.info(
            f"Taking appeal for review: appeal_id={appeal_id}, "
            f"admin_id={self.context.admin_id}"
        )

        result = await self.appeals_service.take_appeal(appeal_id=appeal_id)

        if result.get("success"):
            logger.info(
                f"Appeal taken successfully: appeal_id={appeal_id}, "
                f"admin_id={self.context.admin_id}"
            )
        else:
            logger.warning(
                f"Failed to take appeal: appeal_id={appeal_id}, "
                f"error={result.get('error')}"
            )

        return result

    async def _resolve_appeal(self, tool_input: dict) -> Any:
        """Resolve an appeal with a decision.

        Args:
            tool_input: Dictionary with required 'appeal_id' and 'decision' fields,
                       optional 'notes' field.

        Returns:
            Result dictionary with resolution status.
        """
        appeal_id = tool_input.get("appeal_id")
        decision = tool_input.get("decision")
        notes = tool_input.get("notes")

        if not appeal_id:
            return {"success": False, "error": "appeal_id is required"}

        if not decision:
            return {"success": False, "error": "decision is required"}

        logger.info(
            f"Resolving appeal: appeal_id={appeal_id}, decision={decision}, "
            f"admin_id={self.context.admin_id}"
        )

        result = await self.appeals_service.resolve_appeal(
            appeal_id=appeal_id,
            decision=decision,
            notes=notes,
        )

        if result.get("success"):
            logger.info(
                f"Appeal resolved successfully: appeal_id={appeal_id}, "
                f"decision={decision}, admin_id={self.context.admin_id}"
            )
        else:
            logger.warning(
                f"Failed to resolve appeal: appeal_id={appeal_id}, "
                f"error={result.get('error')}"
            )

        return result

    async def _reply_to_appeal(self, tool_input: dict) -> Any:
        """Send a reply message to the appeal submitter.

        Args:
            tool_input: Dictionary with required 'appeal_id' and 'message' fields.

        Returns:
            Result dictionary with send status.
        """
        appeal_id = tool_input.get("appeal_id")
        message = tool_input.get("message")

        if not appeal_id:
            return {"success": False, "error": "appeal_id is required"}

        if not message:
            return {"success": False, "error": "message is required"}

        logger.info(
            f"Replying to appeal: appeal_id={appeal_id}, "
            f"message_length={len(message)}, admin_id={self.context.admin_id}"
        )

        result = await self.appeals_service.reply_to_appeal(
            appeal_id=appeal_id,
            message=message,
            bot=self.context.bot,
        )

        if result.get("success"):
            logger.info(
                f"Reply sent successfully: appeal_id={appeal_id}, "
                f"admin_id={self.context.admin_id}"
            )
        else:
            logger.warning(
                f"Failed to send reply: appeal_id={appeal_id}, "
                f"error={result.get('error')}"
            )

        return result
