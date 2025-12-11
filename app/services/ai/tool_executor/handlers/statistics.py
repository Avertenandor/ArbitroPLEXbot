"""Statistics tool handler for managing statistics operations.

This module provides the StatisticsToolHandler class for handling statistics-related
tools including deposit stats, bonus stats, withdrawal stats, financial reports, and ROI stats.
"""

import logging
from typing import Any

from ..base import BaseToolHandler, HandlerContext

__all__ = ["StatisticsToolHandler"]

logger = logging.getLogger(__name__)


class StatisticsToolHandler(BaseToolHandler):
    """Handler for statistics-related tools.

    This handler manages all statistics operations including retrieving deposit,
    bonus, withdrawal, financial, and ROI statistics. It delegates to the stats
    service for actual data retrieval operations.

    Attributes:
        context: The handler context containing session, bot, and admin information.
        stats_service: Service instance for performing statistics operations.
    """

    def __init__(self, context: HandlerContext, stats_service: Any) -> None:
        """Initialize the statistics tool handler.

        Args:
            context: Handler context containing necessary execution environment.
            stats_service: Service instance for statistics operations.
        """
        super().__init__(context)
        self.stats_service = stats_service

    def get_tool_names(self) -> set[str]:
        """Get the set of tool names that this handler can process.

        Returns:
            A set containing "get_deposit_stats", "get_bonus_stats",
            "get_withdrawal_stats", "get_financial_report", and "get_roi_stats".
        """
        return {
            "get_deposit_stats",
            "get_bonus_stats",
            "get_withdrawal_stats",
            "get_financial_report",
            "get_roi_stats",
        }

    async def handle(self, tool_name: str, tool_input: dict, **kwargs) -> Any:
        """Handle the execution of a statistics tool.

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
            f"Executing statistics tool '{tool_name}' for admin_id={self.context.admin_id}"
        )

        if tool_name == "get_deposit_stats":
            return await self._get_deposit_stats()
        elif tool_name == "get_bonus_stats":
            return await self._get_bonus_stats()
        elif tool_name == "get_withdrawal_stats":
            return await self._get_withdrawal_stats()
        elif tool_name == "get_financial_report":
            return await self._get_financial_report()
        elif tool_name == "get_roi_stats":
            return await self._get_roi_stats()
        else:
            error_msg = f"Unknown statistics tool: {tool_name}"
            logger.error(error_msg)
            return {"error": error_msg}

    async def _get_deposit_stats(self) -> Any:
        """Get deposit statistics.

        Returns:
            Deposit statistics from the stats service.
        """
        logger.info("Retrieving deposit statistics")
        return await self.stats_service.get_deposit_stats()

    async def _get_bonus_stats(self) -> Any:
        """Get bonus statistics.

        Returns:
            Bonus statistics from the stats service.
        """
        logger.info("Retrieving bonus statistics")
        return await self.stats_service.get_bonus_stats()

    async def _get_withdrawal_stats(self) -> Any:
        """Get withdrawal statistics.

        Returns:
            Withdrawal statistics from the stats service.
        """
        logger.info("Retrieving withdrawal statistics")
        return await self.stats_service.get_withdrawal_stats()

    async def _get_financial_report(self) -> Any:
        """Get financial report.

        Returns:
            Financial report from the stats service.
        """
        logger.info("Retrieving financial report")
        return await self.stats_service.get_financial_report()

    async def _get_roi_stats(self) -> Any:
        """Get ROI statistics.

        Returns:
            ROI statistics from the stats service.
        """
        logger.info("Retrieving ROI statistics")
        return await self.stats_service.get_roi_stats()
