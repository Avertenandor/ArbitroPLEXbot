"""
AI Tool Executor.

Main executor class that orchestrates tool execution using modular handlers.
"""

import logging
from typing import Any

from .base import HandlerContext
from .registry import ToolRegistry
from .services import ServiceRegistry

logger = logging.getLogger(__name__)

__all__ = ["ToolExecutor"]


class ToolExecutor:
    """
    Executes AI tool calls by dispatching to appropriate handlers.

    Uses a registry-based dispatch pattern instead of if/elif chains.
    """

    def __init__(
        self,
        session: Any,
        bot: Any,
        admin_data: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize ToolExecutor.

        Args:
            session: Database session
            bot: Telegram bot instance
            admin_data: Admin user data (ID, username, role, etc.)
        """
        self.session = session
        self.bot = bot
        self.admin_data = admin_data or {}
        self.admin_id = self.admin_data.get("ID", 0)

        # Create context for handlers
        self._context = HandlerContext(
            session=session,
            bot=bot,
            admin_data=self.admin_data,
            admin_id=self.admin_id,
        )

        # Lazy initialization
        self._services: ServiceRegistry | None = None
        self._registry: ToolRegistry | None = None
        self._initialized = False

    def _init_handlers(self) -> None:
        """Initialize all handlers and register them."""
        if self._initialized:
            return

        # Initialize services
        self._services = ServiceRegistry(self.session, self.bot, self.admin_data)
        self._services.init_services()

        # Create registry
        self._registry = ToolRegistry()

        # Import handlers (lazy to avoid circular imports)
        from .handlers import (
            MessagingToolHandler,
            InterviewToolHandler,
            BonusToolHandler,
            AppealsToolHandler,
            InquiriesToolHandler,
            UsersToolHandler,
            StatisticsToolHandler,
            WithdrawalsToolHandler,
            DepositsToolHandler,
            RoiToolHandler,
            BlacklistToolHandler,
            FinpassToolHandler,
            WalletToolHandler,
            ReferralToolHandler,
            LogsToolHandler,
            SettingsToolHandler,
            SecurityToolHandler,
            SystemToolHandler,
            AdminMgmtToolHandler,
        )

        # Create and register handlers
        handlers = [
            MessagingToolHandler(self._context, self._services.get_broadcast_service()),
            InterviewToolHandler(self._context),
            BonusToolHandler(self._context, self._services.get_bonus_service()),
            AppealsToolHandler(self._context, self._services.get_appeals_service()),
            InquiriesToolHandler(self._context, self._services.get_inquiries_service()),
            UsersToolHandler(self._context, self._services.get_users_service()),
            StatisticsToolHandler(self._context, self._services.get_stats_service()),
            WithdrawalsToolHandler(self._context, self._services.get_withdrawals_service()),
            DepositsToolHandler(self._context, self._services.get_deposits_service()),
            RoiToolHandler(self._context, self._services.get_roi_service()),
            BlacklistToolHandler(self._context, self._services.get_blacklist_service()),
            FinpassToolHandler(self._context, self._services.get_finpass_service()),
            WalletToolHandler(self._context),
            ReferralToolHandler(self._context, self._services.get_referral_service()),
            LogsToolHandler(self._context, self._services.get_logs_service()),
            SettingsToolHandler(self._context, self._services.get_settings_service()),
            SecurityToolHandler(self._context),
            SystemToolHandler(self._context),
            AdminMgmtToolHandler(self._context),
        ]

        for handler in handlers:
            self._registry.register_handler(handler)

        self._initialized = True
        logger.info(f"ToolExecutor initialized with {len(self._registry.get_all_tool_names())} tools")

    async def execute(
        self,
        content: list,
        resolve_admin_id_func: Any = None,
    ) -> list[dict]:
        """
        Execute all tool calls in content blocks.

        Args:
            content: List of content blocks from API response
            resolve_admin_id_func: Optional function to resolve admin IDs

        Returns:
            List of tool result dictionaries
        """
        self._init_handlers()
        results = []
        rate_limiter = self._services.get_rate_limiter()

        for block in content:
            # Handle both object and dict formats
            if isinstance(block, dict):
                block_type = block.get("type")
                tool_name = block.get("name")
                tool_input = block.get("input", {})
                tool_id = block.get("id")
            else:
                block_type = getattr(block, "type", None)
                tool_name = getattr(block, "name", None)
                tool_input = getattr(block, "input", {})
                tool_id = getattr(block, "id", None)

            if block_type != "tool_use":
                continue

            # Rate limit check
            allowed, limit_msg = rate_limiter.check_limit(self.admin_id, tool_name)
            if not allowed:
                results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": limit_msg,
                })
                continue

            # Record usage before execution
            rate_limiter.record_usage(self.admin_id, tool_name)
            logger.info(f"ARIA tool execution started: admin={self.admin_id} tool='{tool_name}'")

            try:
                # Get handler and execute
                handler = self._registry.get_handler(tool_name)
                if handler is None:
                    result = {"error": f"Unknown tool: {tool_name}"}
                else:
                    result = await handler.handle(
                        tool_name,
                        tool_input,
                        resolve_admin_id_func=resolve_admin_id_func,
                    )

                results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": str(result),
                })
                logger.info(f"ARIA tool executed successfully: admin={self.admin_id} tool='{tool_name}'")

            except Exception as e:
                logger.error(f"Tool execution error: admin={self.admin_id} tool='{tool_name}' error={e}")
                results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": "Ошибка выполнения операции",
                    "is_error": True,
                })

        return results
