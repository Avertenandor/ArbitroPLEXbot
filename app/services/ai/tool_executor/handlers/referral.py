"""Referral management tool handler.

This module provides the ReferralToolHandler class for managing referral-related operations
in the AI assistant, including platform statistics, user referrals, and top performers.
"""

import logging
from typing import Any

from ..base import BaseToolHandler, HandlerContext
from ..validators import (
    validate_limit,
    validate_user_identifier,
)

__all__ = ["ReferralToolHandler"]

logger = logging.getLogger(__name__)


class ReferralToolHandler(BaseToolHandler):
    """Handler for referral management tools.

    This handler manages all referral-related operations including:
    - Platform-wide referral statistics
    - User-specific referral information
    - Top referrers leaderboard
    - Top earners leaderboard

    Attributes:
        context: Handler context containing session, bot, and admin information.
        referral_service: Service for executing referral management operations.
    """

    def __init__(self, context: HandlerContext, service: Any) -> None:
        """Initialize the referral tool handler.

        Args:
            context: Handler context containing necessary execution environment.
            service: Service instance for referral management operations.
        """
        super().__init__(context)
        self.referral_service = service

    def get_tool_names(self) -> set[str]:
        """Get the set of tool names that this handler can process.

        Returns:
            A set containing all referral management tool names.
        """
        return {
            "get_platform_referral_stats",
            "get_user_referrals",
            "get_top_referrers",
            "get_top_earners",
        }

    async def handle(self, tool_name: str, tool_input: dict, **kwargs) -> Any:
        """Handle the execution of a specific referral management tool.

        Args:
            tool_name: Name of the tool to execute.
            tool_input: Dictionary containing input parameters for the tool.
            **kwargs: Additional keyword arguments for tool execution.

        Returns:
            The result of the tool execution.

        Raises:
            ValueError: If the tool name is unknown or input validation fails.
        """
        logger.info(f"Executing referral management tool: {tool_name}")

        if tool_name == "get_platform_referral_stats":
            return await self._get_platform_referral_stats(tool_input)
        elif tool_name == "get_user_referrals":
            return await self._get_user_referrals(tool_input)
        elif tool_name == "get_top_referrers":
            return await self._get_top_referrers(tool_input)
        elif tool_name == "get_top_earners":
            return await self._get_top_earners(tool_input)
        else:
            raise ValueError(f"Unknown referral management tool: {tool_name}")

    async def _get_platform_referral_stats(self, tool_input: dict) -> Any:
        """Get platform-wide referral statistics.

        Args:
            tool_input: Dictionary (no parameters required).

        Returns:
            Platform referral statistics including total referrals, active referrers, etc.
        """
        logger.debug("Getting platform referral statistics")

        return await self.referral_service.get_platform_referral_stats()

    async def _get_user_referrals(self, tool_input: dict) -> Any:
        """Get referrals for a specific user.

        Args:
            tool_input: Dictionary containing user_identifier and optional limit.

        Returns:
            List of referrals made by the specified user.
        """
        logger.debug("Getting user referrals")

        user_identifier = validate_user_identifier(
            tool_input.get("user_identifier"),
            "user_identifier"
        )
        limit = validate_limit(
            tool_input.get("limit"),
            default=20,
            max_limit=100
        )

        return await self.referral_service.get_user_referrals(
            user_identifier=user_identifier,
            limit=limit
        )

    async def _get_top_referrers(self, tool_input: dict) -> Any:
        """Get top referrers leaderboard.

        Args:
            tool_input: Dictionary containing optional limit.

        Returns:
            List of top referrers ranked by number of referrals.
        """
        logger.debug("Getting top referrers")

        limit = validate_limit(
            tool_input.get("limit"),
            default=20,
            max_limit=100
        )

        return await self.referral_service.get_top_referrers(limit=limit)

    async def _get_top_earners(self, tool_input: dict) -> Any:
        """Get top earners leaderboard from referral commissions.

        Args:
            tool_input: Dictionary containing optional limit.

        Returns:
            List of top earners ranked by referral earnings.
        """
        logger.debug("Getting top earners")

        limit = validate_limit(
            tool_input.get("limit"),
            default=20,
            max_limit=100
        )

        return await self.referral_service.get_top_earners(limit=limit)
