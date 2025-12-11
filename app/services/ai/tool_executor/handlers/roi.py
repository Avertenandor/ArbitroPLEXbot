"""ROI corridor tool handler for managing ROI corridor operations.

This module provides the RoiToolHandler class that manages all ROI corridor-related
tools for the AI assistant, including getting configuration, setting corridors,
and viewing corridor history.
"""

import logging
from typing import Any

from ..base import BaseToolHandler, HandlerContext


__all__ = ["RoiToolHandler"]


logger = logging.getLogger(__name__)


class RoiToolHandler(BaseToolHandler):
    """Handler for ROI corridor management tools.

    This handler manages all ROI corridor-related operations including:
    - Getting ROI configuration
    - Setting ROI corridor parameters
    - Getting corridor history

    Attributes:
        context: Handler context containing session, bot, and admin information.
        roi_service: Service instance for ROI corridor operations.
    """

    def __init__(
        self,
        context: HandlerContext,
        roi_service: Any,
    ) -> None:
        """Initialize the ROI tool handler.

        Args:
            context: Handler context containing necessary execution environment.
            roi_service: Service instance for managing ROI corridors.
        """
        super().__init__(context)
        self.roi_service = roi_service

    def get_tool_names(self) -> set[str]:
        """Get the set of ROI tool names that this handler can process.

        Returns:
            A set containing the 3 ROI tool names.
        """
        return {
            "get_roi_config",
            "set_roi_corridor",
            "get_corridor_history",
        }

    async def handle(self, tool_name: str, tool_input: dict, **kwargs) -> Any:
        """Handle the execution of a specific ROI tool.

        Args:
            tool_name: Name of the tool to execute.
            tool_input: Dictionary containing input parameters for the tool.
            **kwargs: Additional keyword arguments for tool execution.

        Returns:
            The result of the tool execution.

        Raises:
            ValueError: If the tool name is not recognized.
        """
        if tool_name == "get_roi_config":
            return await self._get_roi_config(tool_input)
        elif tool_name == "set_roi_corridor":
            return await self._set_roi_corridor(tool_input)
        elif tool_name == "get_corridor_history":
            return await self._get_corridor_history(tool_input)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def _get_roi_config(self, tool_input: dict) -> dict[str, Any]:
        """Get ROI configuration for a specific level or all levels.

        Args:
            tool_input: Dictionary containing:
                - level (optional): Specific level to get config for

        Returns:
            Result dictionary from the ROI service.
        """
        level = tool_input.get("level")

        logger.info(
            f"Getting ROI config: level={level}, "
            f"admin_id={self.context.admin_id}"
        )

        result = await self.roi_service.get_roi_config(
            level=level,
        )

        logger.info(
            f"ROI config retrieved: level={level}, "
            f"success={result.get('success')}"
        )

        return result

    async def _set_roi_corridor(self, tool_input: dict) -> dict[str, Any]:
        """Set ROI corridor parameters for a specific level.

        Args:
            tool_input: Dictionary containing:
                - level (required): Level to set corridor for
                - mode (required): Corridor mode (e.g., 'range', 'fixed')
                - roi_min (optional): Minimum ROI value
                - roi_max (optional): Maximum ROI value
                - roi_fixed (optional): Fixed ROI value
                - reason (optional): Reason for the change

        Returns:
            Result dictionary from the ROI service.
        """
        level = tool_input.get("level")
        mode = tool_input.get("mode")
        roi_min = tool_input.get("roi_min")
        roi_max = tool_input.get("roi_max")
        roi_fixed = tool_input.get("roi_fixed")
        reason = tool_input.get("reason")

        if not level:
            logger.warning("set_roi_corridor called without level")
            return {
                "success": False,
                "error": "❌ level is required"
            }

        if not mode:
            logger.warning("set_roi_corridor called without mode")
            return {
                "success": False,
                "error": "❌ mode is required"
            }

        logger.info(
            f"Setting ROI corridor: level={level}, mode={mode}, "
            f"roi_min={roi_min}, roi_max={roi_max}, roi_fixed={roi_fixed}, "
            f"has_reason={bool(reason)}, admin_id={self.context.admin_id}"
        )

        result = await self.roi_service.set_roi_corridor(
            level=level,
            mode=mode,
            roi_min=roi_min,
            roi_max=roi_max,
            roi_fixed=roi_fixed,
            reason=reason,
        )

        logger.info(
            f"ROI corridor set result: level={level}, mode={mode}, "
            f"success={result.get('success')}"
        )

        return result

    async def _get_corridor_history(self, tool_input: dict) -> dict[str, Any]:
        """Get history of ROI corridor changes.

        Args:
            tool_input: Dictionary containing:
                - level (optional): Filter by specific level
                - limit (optional): Maximum number of history entries to return (default 20)

        Returns:
            Result dictionary from the ROI service.
        """
        level = tool_input.get("level")
        limit = tool_input.get("limit", 20)

        logger.info(
            f"Getting corridor history: level={level}, limit={limit}, "
            f"admin_id={self.context.admin_id}"
        )

        result = await self.roi_service.get_corridor_history(
            level=level,
            limit=limit,
        )

        logger.info(
            f"Corridor history retrieved: level={level}, "
            f"success={result.get('success')}, "
            f"count={result.get('total_count', 0)}"
        )

        return result
