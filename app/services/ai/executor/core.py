"""
AI Tool Executor Core.

Main ToolExecutor class that dispatches tool calls to handlers.
Separates tool execution logic from the main AI assistant service.

ВАЖНО: Арья является администратором (extended_admin)
и выполняет команды от имени системы. Проверка авторизации
собеседника происходит в ai_assistant_service.py ПЕРЕД
вызовом ToolExecutor.
"""

import logging
from typing import Any

from app.config.security import (
    get_arya_role,
    is_arya_admin,
)
from app.services.ai.executor.admin_handlers import AdminHandlersMixin
from app.services.ai.executor.deposit_handlers import DepositHandlersMixin
from app.services.ai.executor.message_handlers import (
    MessageHandlersMixin,
)
from app.services.ai.executor.system_handlers import SystemHandlersMixin
from app.services.ai.executor.tool_registry import ToolRegistryMixin
from app.services.ai.executor.user_handlers import UserHandlersMixin
from app.services.ai.executor.withdrawal_handlers import (
    WithdrawalHandlersMixin,
)


logger = logging.getLogger(__name__)


class ToolExecutor(
    MessageHandlersMixin,
    UserHandlersMixin,
    DepositHandlersMixin,
    WithdrawalHandlersMixin,
    AdminHandlersMixin,
    SystemHandlersMixin,
    ToolRegistryMixin,
):
    """
    Executes AI tool calls by dispatching to appropriate services.

    ВАЖНО: Арья сама является администратором (extended_admin)!
    Инструменты выполняются от имени АРЬИ, не от имени
    собеседника.

    Проверка авторизации собеседника (can_command_arya)
    происходит в ai_assistant_service.py ПЕРЕД созданием
    ToolExecutor.

    Handles tool execution, rate limiting, error handling,
    and logging.
    """

    def __init__(
        self,
        session: Any,
        bot: Any,
        admin_data: dict[str, Any] | None = None,
        caller_telegram_id: int | None = None,
    ):
        """
        Initialize ToolExecutor.

        Args:
            session: Database session
            bot: Telegram bot instance
            admin_data: Admin user data (ID, username, role, etc.)
                       Это данные СОБЕСЕДНИКА, не Арьи!
            caller_telegram_id: Telegram ID того, кто даёт команду Арье
        """
        self.session = session
        self.bot = bot
        self.admin_data = admin_data or {}
        self.caller_telegram_id = caller_telegram_id

        # ВАЖНО: admin_id для логирования = ID АРЬИ (виртуальный)
        # но для rate limiting используем ID собеседника
        self.admin_id = self.admin_data.get("ID", 0)

        # Проверка что Арья - администратор (всегда True)
        if not is_arya_admin():
            logger.error(
                "CRITICAL: Арья не является администратором! "
                "Проверьте security.py"
            )

        logger.debug(
            f"ToolExecutor: Арья (role={get_arya_role()}) "
            f"выполняет команды от caller_id={caller_telegram_id}"
        )

        # Initialize services lazily to avoid circular imports
        self._services_initialized = False
        self._broadcast_service = None
        self._bonus_service = None
        self._appeals_service = None
        self._inquiries_service = None
        self._users_service = None
        self._stats_service = None
        self._withdrawals_service = None
        self._deposits_service = None
        self._roi_service = None
        self._blacklist_service = None
        self._finpass_service = None
        self._referral_service = None
        self._logs_service = None
        self._settings_service = None
        self._rate_limiter = None

    def _init_services(self) -> None:
        """Initialize all services lazily."""
        if self._services_initialized:
            return

        from app.services.ai_appeals_service import AIAppealsService
        from app.services.ai_blacklist_service import AIBlacklistService
        from app.services.ai_bonus_service import AIBonusService
        from app.services.ai_broadcast_service import AIBroadcastService
        from app.services.ai_deposits_service import AIDepositsService
        from app.services.ai_finpass_service import AIFinpassService
        from app.services.ai_inquiries_service import AIInquiriesService
        from app.services.ai_logs_service import AILogsService
        from app.services.ai_referral_service import AIReferralService
        from app.services.ai_roi_service import AIRoiService
        from app.services.ai_settings import AISettingsService
        from app.services.ai_statistics_service import (
            AIStatisticsService,
        )
        from app.services.ai_users import AIUsersService
        from app.services.ai_withdrawals_service import (
            AIWithdrawalsService,
        )
        from app.services.aria_security_defense import get_rate_limiter

        self._broadcast_service = AIBroadcastService(
            self.session,
            self.bot,
            admin_telegram_id=self.admin_data.get("ID"),
            admin_username=self.admin_data.get("username"),
        )
        self._bonus_service = AIBonusService(
            self.session, self.admin_data
        )
        self._appeals_service = AIAppealsService(
            self.session, self.admin_data
        )
        self._inquiries_service = AIInquiriesService(
            self.session, self.admin_data
        )
        self._users_service = AIUsersService(
            self.session, self.admin_data
        )
        self._stats_service = AIStatisticsService(
            self.session, self.admin_data
        )
        self._withdrawals_service = AIWithdrawalsService(
            self.session, self.admin_data
        )
        self._deposits_service = AIDepositsService(
            self.session, self.admin_data
        )
        self._roi_service = AIRoiService(self.session, self.admin_data)
        self._blacklist_service = AIBlacklistService(
            self.session, self.admin_data
        )
        self._finpass_service = AIFinpassService(
            self.session, self.admin_data
        )
        self._referral_service = AIReferralService(
            self.session, self.admin_data
        )
        self._logs_service = AILogsService(self.session, self.admin_data)
        self._settings_service = AISettingsService(
            self.session, self.admin_data
        )
        self._rate_limiter = get_rate_limiter()

        self._services_initialized = True

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
        self._init_services()
        results = []

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

            # Check rate limit BEFORE execution to prevent abuse
            allowed, limit_msg = self._rate_limiter.check_limit(
                self.admin_id, tool_name
            )
            if not allowed:
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": limit_msg,
                    }
                )
                continue

            # Record usage BEFORE execution to prevent retry-abuse
            # (if user retries failed request, it still counts)
            self._rate_limiter.record_usage(self.admin_id, tool_name)
            logger.info(
                f"ARIA tool execution started: admin={self.admin_id} "
                f"tool='{tool_name}'"
            )

            try:
                result = await self._execute_tool(
                    tool_name, tool_input, resolve_admin_id_func
                )
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": str(result),
                    }
                )
                self._rate_limiter.record_usage(self.admin_id, tool_name)
                logger.info(
                    f"ARIA tool executed: admin={self.admin_id} "
                    f"tool='{tool_name}'"
                )

            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": "Ошибка выполнения операции",
                        "is_error": True,
                    }
                )

        return results

    async def _execute_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        resolve_admin_id_func: Any = None,
    ) -> Any:
        """
        Execute a single tool by name.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool
            resolve_admin_id_func: Optional function to resolve admin IDs

        Returns:
            Tool execution result
        """
        # Messaging tools
        if tool_name in self._get_messaging_tool_names():
            return await self._execute_messaging_tool(
                tool_name, tool_input
            )

        # Interview tools
        if tool_name in (
            "start_interview",
            "get_interview_status",
            "cancel_interview",
            "get_knowledge_by_user",
        ):
            return await self._execute_interview_tool(
                tool_name, tool_input, resolve_admin_id_func
            )

        # Bonus tools
        if tool_name in ("grant_bonus", "get_user_bonuses", "cancel_bonus"):
            return await self._execute_bonus_tool(tool_name, tool_input)

        # Appeals tools
        if tool_name in self._get_appeals_tool_names():
            return await self._execute_appeals_tool(tool_name, tool_input)

        # Inquiries tools
        if tool_name in self._get_inquiries_tool_names():
            return await self._execute_inquiries_tool(
                tool_name, tool_input
            )

        # User management tools
        if tool_name in self._get_user_tool_names():
            return await self._execute_user_tool(tool_name, tool_input)

        # Statistics tools
        if tool_name in self._get_stats_tool_names():
            return await self._execute_stats_tool(tool_name, tool_input)

        # Withdrawals tools
        if tool_name in self._get_withdrawals_tool_names():
            return await self._execute_withdrawals_tool(
                tool_name, tool_input
            )

        # System administration tools
        if tool_name in self._get_system_tool_names():
            return await self._execute_system_tool(tool_name, tool_input)

        # Admin management tools
        if tool_name in self._get_admin_mgmt_tool_names():
            return await self._execute_admin_mgmt_tool(
                tool_name, tool_input
            )

        # Deposits tools
        if tool_name in self._get_deposits_tool_names():
            return await self._execute_deposits_tool(tool_name, tool_input)

        # ROI tools
        if tool_name in (
            "get_roi_config",
            "set_roi_corridor",
            "get_corridor_history",
        ):
            return await self._execute_roi_tool(tool_name, tool_input)

        # Blacklist tools
        if tool_name in self._get_blacklist_tool_names():
            return await self._execute_blacklist_tool(
                tool_name, tool_input
            )

        # Finpass tools
        if tool_name in self._get_finpass_tool_names():
            return await self._execute_finpass_tool(tool_name, tool_input)

        # Wallet tools
        if tool_name in (
            "check_user_wallet",
            "get_plex_rate",
            "get_wallet_summary_for_dialog",
        ):
            return await self._execute_wallet_tool(tool_name, tool_input)

        # Referral tools
        if tool_name in self._get_referral_tool_names():
            return await self._execute_referral_tool(tool_name, tool_input)

        # Logs tools
        if tool_name in self._get_logs_tool_names():
            return await self._execute_logs_tool(tool_name, tool_input)

        # Settings tools
        if tool_name in self._get_settings_tool_names():
            return await self._execute_settings_tool(tool_name, tool_input)

        # Security tools
        if tool_name in (
            "check_username_spoofing",
            "get_verified_admins",
            "verify_admin_identity",
        ):
            return await self._execute_security_tool(
                tool_name, tool_input
            )

        return {"error": f"Unknown tool: {tool_name}"}
