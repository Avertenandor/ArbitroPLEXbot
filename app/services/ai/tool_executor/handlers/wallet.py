"""Wallet management tool handler.

This module provides the WalletToolHandler class for managing wallet-related operations
in the AI assistant, including checking wallet balances, PLEX rates, and wallet summaries.
"""

import logging
from typing import Any

from app.services.ai_wallet_service import AIWalletService

from ..base import BaseToolHandler, HandlerContext
from ..validators import validate_positive_int, validate_user_identifier

__all__ = ["WalletToolHandler"]

logger = logging.getLogger(__name__)


class WalletToolHandler(BaseToolHandler):
    """Handler for wallet management tools.

    This handler manages all wallet-related operations including:
    - Checking user wallet balances (BNB, USDT, PLEX)
    - Getting current PLEX exchange rate
    - Getting wallet summaries for dialog context

    Note: This handler creates AIWalletService on-demand rather than
    using a pre-initialized service instance.

    Attributes:
        context: Handler context containing session, bot, and admin information.
    """

    def __init__(self, context: HandlerContext) -> None:
        """Initialize the wallet tool handler.

        Args:
            context: Handler context containing necessary execution environment.
        """
        super().__init__(context)

    def get_tool_names(self) -> set[str]:
        """Get the set of tool names that this handler can process.

        Returns:
            A set containing all wallet management tool names.
        """
        return {
            "check_user_wallet",
            "get_plex_rate",
            "get_wallet_summary_for_dialog",
        }

    async def handle(self, tool_name: str, tool_input: dict, **kwargs) -> Any:
        """Handle the execution of a specific wallet management tool.

        Args:
            tool_name: Name of the tool to execute.
            tool_input: Dictionary containing input parameters for the tool.
            **kwargs: Additional keyword arguments for tool execution.

        Returns:
            The result of the tool execution.

        Raises:
            ValueError: If the tool name is unknown or input validation fails.
        """
        logger.info(f"Executing wallet management tool: {tool_name}")

        if tool_name == "check_user_wallet":
            return await self._check_user_wallet(tool_input)
        elif tool_name == "get_plex_rate":
            return await self._get_plex_rate(tool_input)
        elif tool_name == "get_wallet_summary_for_dialog":
            return await self._get_wallet_summary_for_dialog(tool_input)
        else:
            raise ValueError(f"Unknown wallet management tool: {tool_name}")

    async def _check_user_wallet(self, tool_input: dict) -> Any:
        """Check user wallet balances.

        This tool retrieves wallet balance information for a user, including
        BNB, USDT, and PLEX balances, along with recommendations and warnings.

        Args:
            tool_input: Dictionary containing user_identifier.

        Returns:
            Dictionary with wallet balance information, recommendations, and warnings.
        """
        logger.debug("Checking user wallet")

        user_identifier = validate_user_identifier(
            tool_input.get("user_identifier"),
            "user_identifier"
        )

        # Create wallet service on-demand
        wallet_service = AIWalletService(
            self.context.session,
            self.context.admin_data
        )

        return await wallet_service.check_user_wallet(
            user_identifier=user_identifier
        )

    async def _get_plex_rate(self, tool_input: dict) -> Any:
        """Get current PLEX exchange rate.

        This tool retrieves the current PLEX token exchange rate and economics,
        including daily, weekly, and monthly projections.

        Args:
            tool_input: Dictionary (no parameters required).

        Returns:
            Dictionary with PLEX rate information and economics.
        """
        logger.debug("Getting PLEX rate")

        # Create wallet service on-demand
        wallet_service = AIWalletService(
            self.context.session,
            self.context.admin_data
        )

        return await wallet_service.get_plex_rate()

    async def _get_wallet_summary_for_dialog(self, tool_input: dict) -> Any:
        """Get wallet summary for dialog context.

        This tool retrieves a wallet summary specifically formatted for use
        in dialog contexts, including end-of-dialog prompts and recommendations.

        Args:
            tool_input: Dictionary containing user_telegram_id.

        Returns:
            Dictionary with wallet summary and dialog-appropriate messaging.
        """
        logger.debug("Getting wallet summary for dialog")

        user_telegram_id = validate_positive_int(
            tool_input.get("user_telegram_id"),
            "user_telegram_id"
        )

        # Create wallet service on-demand
        wallet_service = AIWalletService(
            self.context.session,
            self.context.admin_data
        )

        return await wallet_service.get_wallet_summary_for_dialog_end(
            user_telegram_id=user_telegram_id
        )
