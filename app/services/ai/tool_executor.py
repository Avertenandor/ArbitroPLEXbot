"""
AI Tool Executor.

Executes AI tool calls by dispatching to appropriate services.
Separates tool execution logic from the main AI assistant service.
"""

import logging
from decimal import Decimal, InvalidOperation
from typing import Any

logger = logging.getLogger(__name__)


# ========== Input Validation Helpers ==========

def validate_required_string(value: Any, field_name: str, max_length: int = 1000) -> str:
    """Validate and sanitize a required string field."""
    if value is None:
        raise ValueError(f"{field_name} is required")
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} cannot be empty")
    if len(value) > max_length:
        value = value[:max_length]
    return value


def validate_optional_string(value: Any, field_name: str, max_length: int = 1000) -> str | None:
    """Validate and sanitize an optional string field."""
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if not value:
        return None
    if len(value) > max_length:
        value = value[:max_length]
    return value


def validate_positive_int(value: Any, field_name: str, max_value: int = 1000000) -> int:
    """Validate a positive integer field."""
    if value is None:
        raise ValueError(f"{field_name} is required")
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be an integer")
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")
    if value > max_value:
        value = max_value
    return value


def validate_positive_decimal(value: Any, field_name: str, max_value: Decimal = Decimal("1000000000")) -> Decimal:
    """Validate a positive decimal field."""
    if value is None:
        raise ValueError(f"{field_name} is required")
    try:
        value = Decimal(str(value))
    except (TypeError, ValueError, InvalidOperation):
        raise ValueError(f"{field_name} must be a number")
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")
    if value > max_value:
        raise ValueError(f"{field_name} exceeds maximum allowed value")
    return value


def validate_user_identifier(value: Any, field_name: str = "user_identifier") -> str:
    """Validate a user identifier (telegram_id or @username)."""
    if value is None:
        raise ValueError(f"{field_name} is required")
    value = str(value).strip()
    if not value:
        raise ValueError(f"{field_name} cannot be empty")
    # Accept: numeric ID, @username, or plain username
    if value.startswith("@"):
        if len(value) < 2:
            raise ValueError(f"{field_name}: invalid username format")
    elif not value.isdigit():
        # Allow alphanumeric usernames without @
        if not all(c.isalnum() or c == "_" for c in value):
            raise ValueError(f"{field_name}: invalid format")
    return value


def validate_limit(value: Any, default: int = 20, max_limit: int = 100) -> int:
    """Validate a limit parameter."""
    if value is None:
        return default
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    if value <= 0:
        return default
    if value > max_limit:
        return max_limit
    return value


class ToolExecutor:
    """
    Executes AI tool calls by dispatching to appropriate services.
    
    Handles tool execution, rate limiting, error handling, and logging.
    """

    def __init__(
        self,
        session: Any,
        bot: Any,
        admin_data: dict[str, Any] | None = None,
    ):
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

        from app.services.ai_bonus_service import AIBonusService
        from app.services.ai_appeals_service import AIAppealsService
        from app.services.ai_blacklist_service import AIBlacklistService
        from app.services.ai_broadcast_service import AIBroadcastService
        from app.services.ai_deposits_service import AIDepositsService
        from app.services.ai_finpass_service import AIFinpassService
        from app.services.ai_inquiries_service import AIInquiriesService
        from app.services.ai_logs_service import AILogsService
        from app.services.ai_referral_service import AIReferralService
        from app.services.ai_roi_service import AIRoiService
        from app.services.ai_settings_service import AISettingsService
        from app.services.ai_statistics_service import AIStatisticsService
        from app.services.ai_users_service import AIUsersService
        from app.services.ai_withdrawals_service import AIWithdrawalsService
        from app.services.aria_security_defense import get_rate_limiter

        self._broadcast_service = AIBroadcastService(
            self.session,
            self.bot,
            admin_telegram_id=self.admin_data.get("ID"),
            admin_username=self.admin_data.get("username"),
        )
        self._bonus_service = AIBonusService(self.session, self.admin_data)
        self._appeals_service = AIAppealsService(self.session, self.admin_data)
        self._inquiries_service = AIInquiriesService(self.session, self.admin_data)
        self._users_service = AIUsersService(self.session, self.admin_data)
        self._stats_service = AIStatisticsService(self.session, self.admin_data)
        self._withdrawals_service = AIWithdrawalsService(self.session, self.admin_data)
        self._deposits_service = AIDepositsService(self.session, self.admin_data)
        self._roi_service = AIRoiService(self.session, self.admin_data)
        self._blacklist_service = AIBlacklistService(self.session, self.admin_data)
        self._finpass_service = AIFinpassService(self.session, self.admin_data)
        self._referral_service = AIReferralService(self.session, self.admin_data)
        self._logs_service = AILogsService(self.session, self.admin_data)
        self._settings_service = AISettingsService(self.session, self.admin_data)
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
            allowed, limit_msg = self._rate_limiter.check_limit(self.admin_id, tool_name)
            if not allowed:
                results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": limit_msg,
                })
                continue

            # Record usage BEFORE execution to prevent retry-abuse
            # (if user retries failed request, it still counts towards limit)
            self._rate_limiter.record_usage(self.admin_id, tool_name)
            logger.info(f"ARIA tool execution started: admin={self.admin_id} tool='{tool_name}'")

            try:
                result = await self._execute_tool(
                    tool_name, tool_input, resolve_admin_id_func
                )
                results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": str(result),
                })
                logger.info(f"ARIA tool executed successfully: admin={self.admin_id} tool='{tool_name}'")

            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": "Ошибка выполнения операции",
                    "is_error": True,
                })

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
            return await self._execute_messaging_tool(tool_name, tool_input)

        # Interview tools
        if tool_name in ("start_interview", "get_interview_status", "cancel_interview"):
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
            return await self._execute_inquiries_tool(tool_name, tool_input)

        # User management tools
        if tool_name in self._get_user_tool_names():
            return await self._execute_user_tool(tool_name, tool_input)

        # Statistics tools
        if tool_name in self._get_stats_tool_names():
            return await self._execute_stats_tool(tool_name, tool_input)

        # Withdrawals tools
        if tool_name in self._get_withdrawals_tool_names():
            return await self._execute_withdrawals_tool(tool_name, tool_input)

        # System administration tools
        if tool_name in self._get_system_tool_names():
            return await self._execute_system_tool(tool_name, tool_input)

        # Admin management tools
        if tool_name in self._get_admin_mgmt_tool_names():
            return await self._execute_admin_mgmt_tool(tool_name, tool_input)

        # Deposits tools
        if tool_name in self._get_deposits_tool_names():
            return await self._execute_deposits_tool(tool_name, tool_input)

        # ROI tools
        if tool_name in ("get_roi_config", "set_roi_corridor", "get_corridor_history"):
            return await self._execute_roi_tool(tool_name, tool_input)

        # Blacklist tools
        if tool_name in self._get_blacklist_tool_names():
            return await self._execute_blacklist_tool(tool_name, tool_input)

        # Finpass tools
        if tool_name in self._get_finpass_tool_names():
            return await self._execute_finpass_tool(tool_name, tool_input)

        # Wallet tools
        if tool_name in ("check_user_wallet", "get_plex_rate", "get_wallet_summary_for_dialog"):
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
        if tool_name in ("check_username_spoofing", "get_verified_admins", "verify_admin_identity"):
            return await self._execute_security_tool(tool_name, tool_input)

        return {"error": f"Unknown tool: {tool_name}"}

    # ========== Tool name getters ==========

    def _get_messaging_tool_names(self) -> set[str]:
        return {
            "send_message_to_user", "broadcast_to_group", "get_users_list",
            "invite_to_dialog", "mass_invite_to_dialog"
        }

    def _get_appeals_tool_names(self) -> set[str]:
        return {
            "get_appeals_list", "get_appeal_details", "take_appeal",
            "resolve_appeal", "reply_to_appeal"
        }

    def _get_inquiries_tool_names(self) -> set[str]:
        return {
            "get_inquiries_list", "get_inquiry_details", "take_inquiry",
            "reply_to_inquiry", "close_inquiry"
        }

    def _get_user_tool_names(self) -> set[str]:
        return {
            "get_user_profile", "search_users", "change_user_balance",
            "block_user", "unblock_user", "get_user_deposits", "get_users_stats"
        }

    def _get_stats_tool_names(self) -> set[str]:
        return {
            "get_deposit_stats", "get_bonus_stats", "get_withdrawal_stats",
            "get_financial_report", "get_roi_stats"
        }

    def _get_withdrawals_tool_names(self) -> set[str]:
        return {
            "get_pending_withdrawals", "get_withdrawal_details",
            "approve_withdrawal", "reject_withdrawal", "get_withdrawals_statistics"
        }

    def _get_system_tool_names(self) -> set[str]:
        return {
            "get_emergency_status", "emergency_full_stop", "emergency_full_resume",
            "toggle_emergency_deposits", "toggle_emergency_withdrawals",
            "toggle_emergency_roi", "get_blockchain_status", "switch_rpc_provider",
            "toggle_rpc_auto_switch", "get_platform_health", "get_global_settings"
        }

    def _get_admin_mgmt_tool_names(self) -> set[str]:
        return {
            "get_admins_list", "get_admin_details", "block_admin",
            "unblock_admin", "change_admin_role", "get_admin_stats"
        }

    def _get_deposits_tool_names(self) -> set[str]:
        return {
            "get_deposit_levels_config", "get_user_deposits_list",
            "get_pending_deposits", "get_deposit_details",
            "get_platform_deposit_stats", "change_max_deposit_level",
            "create_manual_deposit", "modify_deposit_roi",
            "cancel_deposit", "confirm_deposit"
        }

    def _get_blacklist_tool_names(self) -> set[str]:
        return {"get_blacklist", "check_blacklist", "add_to_blacklist", "remove_from_blacklist"}

    def _get_finpass_tool_names(self) -> set[str]:
        return {
            "get_finpass_requests", "get_finpass_request_details",
            "approve_finpass_request", "reject_finpass_request", "get_finpass_stats"
        }

    def _get_referral_tool_names(self) -> set[str]:
        return {
            "get_platform_referral_stats", "get_user_referrals",
            "get_top_referrers", "get_top_earners"
        }

    def _get_logs_tool_names(self) -> set[str]:
        return {
            "get_recent_logs", "get_admin_activity",
            "search_logs", "get_action_types_stats"
        }

    def _get_settings_tool_names(self) -> set[str]:
        return {
            "get_withdrawal_settings", "set_min_withdrawal", "toggle_daily_limit",
            "set_daily_limit", "toggle_auto_withdrawal", "set_service_fee",
            "get_deposit_settings", "set_level_corridor", "toggle_deposit_level",
            "set_plex_rate", "get_scheduled_tasks", "trigger_task",
            "create_admin", "delete_admin"
        }

    # ========== Tool execution methods ==========

    async def _execute_messaging_tool(self, name: str, inp: dict) -> Any:
        """Execute messaging/broadcast tools."""
        if name == "send_message_to_user":
            user_id = validate_user_identifier(inp.get("user_identifier"))
            message = validate_required_string(inp.get("message_text"), "message_text", max_length=4000)
            return await self._broadcast_service.send_message_to_user(
                user_identifier=user_id,
                message_text=message,
            )
        elif name == "broadcast_to_group":
            group = validate_required_string(inp.get("group"), "group", max_length=50)
            message = validate_required_string(inp.get("message_text"), "message_text", max_length=4000)
            limit = validate_limit(inp.get("limit"), default=100, max_limit=1000)
            return await self._broadcast_service.broadcast_to_group(
                group=group,
                message_text=message,
                limit=limit,
            )
        elif name == "get_users_list":
            group = validate_required_string(inp.get("group"), "group", max_length=50)
            limit = validate_limit(inp.get("limit"), default=20, max_limit=100)
            return await self._broadcast_service.get_users_list(
                group=group,
                limit=limit,
            )
        elif name == "invite_to_dialog":
            user_id = validate_user_identifier(inp.get("user_identifier"))
            custom_msg = validate_optional_string(inp.get("custom_message"), "custom_message", max_length=500)
            return await self._broadcast_service.invite_to_dialog(
                user_identifier=user_id,
                custom_message=custom_msg,
            )
        elif name == "mass_invite_to_dialog":
            group = validate_required_string(inp.get("group"), "group", max_length=50)
            custom_msg = validate_optional_string(inp.get("custom_message"), "custom_message", max_length=500)
            limit = validate_limit(inp.get("limit"), default=50, max_limit=200)
            return await self._broadcast_service.mass_invite_to_dialog(
                group=group,
                custom_message=custom_msg,
                limit=limit,
            )
        return {"error": "Unknown messaging tool"}

    async def _execute_interview_tool(
        self, name: str, inp: dict, resolve_admin_id_func: Any
    ) -> Any:
        """Execute interview tools."""
        from app.services.ai_interview_service import get_interview_service, init_interview_service

        interview_service = get_interview_service(self.bot)
        if not interview_service:
            interview_service = init_interview_service(self.bot)

        if name == "start_interview":
            if not resolve_admin_id_func:
                return {"success": False, "error": "Функция поиска админа недоступна"}
            admin_id = await resolve_admin_id_func(inp["admin_identifier"], self.session)
            if not admin_id:
                return {"success": False, "error": f"Админ '{inp['admin_identifier']}' не найден"}
            return await interview_service.start_interview(
                interviewer_id=self.admin_data.get("ID", 0),
                target_admin_id=admin_id["telegram_id"],
                target_admin_username=admin_id["username"] or str(admin_id["telegram_id"]),
                topic=inp["topic"],
                questions=inp["questions"],
            )
        elif name == "get_interview_status":
            if not resolve_admin_id_func:
                return {"success": False, "error": "Функция поиска админа недоступна"}
            admin_id = await resolve_admin_id_func(inp["admin_identifier"], self.session)
            if not admin_id:
                return {"success": False, "error": "Админ не найден"}
            status = interview_service.get_interview_status(admin_id["telegram_id"])
            return status if status else {"success": False, "error": "Нет активного интервью"}
        elif name == "cancel_interview":
            if not resolve_admin_id_func:
                return {"success": False, "error": "Функция поиска админа недоступна"}
            admin_id = await resolve_admin_id_func(inp["admin_identifier"], self.session)
            if not admin_id:
                return {"success": False, "error": "Админ не найден"}
            return await interview_service.cancel_interview(admin_id["telegram_id"])
        return {"error": "Unknown interview tool"}

    async def _execute_bonus_tool(self, name: str, inp: dict) -> Any:
        """Execute bonus tools."""
        if name == "grant_bonus":
            user_id = validate_user_identifier(inp.get("user_identifier"))
            amount = validate_positive_decimal(inp.get("amount"), "amount")
            reason = validate_required_string(inp.get("reason"), "reason", max_length=500)
            return await self._bonus_service.grant_bonus(
                user_identifier=user_id,
                amount=amount,
                reason=reason,
            )
        elif name == "get_user_bonuses":
            user_id = validate_user_identifier(inp.get("user_identifier"))
            return await self._bonus_service.get_user_bonuses(
                user_identifier=user_id,
                active_only=bool(inp.get("active_only", False)),
            )
        elif name == "cancel_bonus":
            bonus_id = validate_positive_int(inp.get("bonus_id"), "bonus_id")
            reason = validate_required_string(inp.get("reason"), "reason", max_length=500)
            return await self._bonus_service.cancel_bonus(
                bonus_id=bonus_id,
                reason=reason,
            )
        return {"error": "Unknown bonus tool"}

    async def _execute_appeals_tool(self, name: str, inp: dict) -> Any:
        """Execute appeals tools."""
        if name == "get_appeals_list":
            return await self._appeals_service.get_appeals_list(
                status=inp.get("status"),
                limit=inp.get("limit", 20),
            )
        elif name == "get_appeal_details":
            return await self._appeals_service.get_appeal_details(appeal_id=inp["appeal_id"])
        elif name == "take_appeal":
            return await self._appeals_service.take_appeal(appeal_id=inp["appeal_id"])
        elif name == "resolve_appeal":
            return await self._appeals_service.resolve_appeal(
                appeal_id=inp["appeal_id"],
                decision=inp["decision"],
                notes=inp.get("notes"),
            )
        elif name == "reply_to_appeal":
            return await self._appeals_service.reply_to_appeal(
                appeal_id=inp["appeal_id"],
                message=inp["message"],
                bot=self.bot,
            )
        return {"error": "Unknown appeals tool"}

    async def _execute_inquiries_tool(self, name: str, inp: dict) -> Any:
        """Execute inquiries tools."""
        if name == "get_inquiries_list":
            return await self._inquiries_service.get_inquiries_list(
                status=inp.get("status"),
                limit=inp.get("limit", 20),
            )
        elif name == "get_inquiry_details":
            return await self._inquiries_service.get_inquiry_details(inquiry_id=inp["inquiry_id"])
        elif name == "take_inquiry":
            return await self._inquiries_service.take_inquiry(inquiry_id=inp["inquiry_id"])
        elif name == "reply_to_inquiry":
            return await self._inquiries_service.reply_to_inquiry(
                inquiry_id=inp["inquiry_id"],
                message=inp["message"],
                bot=self.bot,
            )
        elif name == "close_inquiry":
            return await self._inquiries_service.close_inquiry(
                inquiry_id=inp["inquiry_id"],
                reason=inp.get("reason"),
            )
        return {"error": "Unknown inquiries tool"}

    async def _execute_user_tool(self, name: str, inp: dict) -> Any:
        """Execute user management tools."""
        if name == "get_user_profile":
            user_id = validate_user_identifier(inp.get("user_identifier"))
            return await self._users_service.get_user_profile(user_identifier=user_id)
        elif name == "search_users":
            query = validate_required_string(inp.get("query"), "query", max_length=100)
            limit = validate_limit(inp.get("limit"), default=20, max_limit=50)
            return await self._users_service.search_users(
                query=query,
                limit=limit,
            )
        elif name == "change_user_balance":
            user_id = validate_user_identifier(inp.get("user_identifier"))
            amount = validate_positive_decimal(inp.get("amount"), "amount")
            reason = validate_required_string(inp.get("reason"), "reason", max_length=500)
            operation = validate_required_string(inp.get("operation"), "operation", max_length=20)
            if operation not in ("add", "subtract", "set"):
                raise ValueError("operation must be 'add', 'subtract', or 'set'")
            return await self._users_service.change_user_balance(
                user_identifier=user_id,
                amount=amount,
                reason=reason,
                operation=operation,
            )
        elif name == "block_user":
            user_id = validate_user_identifier(inp.get("user_identifier"))
            reason = validate_required_string(inp.get("reason"), "reason", max_length=500)
            return await self._users_service.block_user(
                user_identifier=user_id,
                reason=reason,
            )
        elif name == "unblock_user":
            user_id = validate_user_identifier(inp.get("user_identifier"))
            return await self._users_service.unblock_user(user_identifier=user_id)
        elif name == "get_user_deposits":
            user_id = validate_user_identifier(inp.get("user_identifier"))
            return await self._users_service.get_user_deposits(user_identifier=user_id)
        elif name == "get_users_stats":
            return await self._users_service.get_users_stats()
        return {"error": "Unknown user tool"}

    async def _execute_stats_tool(self, name: str, inp: dict) -> Any:
        """Execute statistics tools."""
        if name == "get_deposit_stats":
            return await self._stats_service.get_deposit_stats()
        elif name == "get_bonus_stats":
            return await self._stats_service.get_bonus_stats()
        elif name == "get_withdrawal_stats":
            return await self._stats_service.get_withdrawal_stats()
        elif name == "get_financial_report":
            return await self._stats_service.get_financial_report()
        elif name == "get_roi_stats":
            return await self._stats_service.get_roi_stats()
        return {"error": "Unknown stats tool"}

    async def _execute_withdrawals_tool(self, name: str, inp: dict) -> Any:
        """Execute withdrawals tools."""
        if name == "get_pending_withdrawals":
            limit = validate_limit(inp.get("limit"), default=20, max_limit=100)
            return await self._withdrawals_service.get_pending_withdrawals(limit=limit)
        elif name == "get_withdrawal_details":
            withdrawal_id = validate_positive_int(inp.get("withdrawal_id"), "withdrawal_id")
            return await self._withdrawals_service.get_withdrawal_details(withdrawal_id=withdrawal_id)
        elif name == "approve_withdrawal":
            withdrawal_id = validate_positive_int(inp.get("withdrawal_id"), "withdrawal_id")
            tx_hash = validate_optional_string(inp.get("tx_hash"), "tx_hash", max_length=100)
            return await self._withdrawals_service.approve_withdrawal(
                withdrawal_id=withdrawal_id,
                tx_hash=tx_hash,
            )
        elif name == "reject_withdrawal":
            withdrawal_id = validate_positive_int(inp.get("withdrawal_id"), "withdrawal_id")
            reason = validate_required_string(inp.get("reason"), "reason", max_length=500)
            return await self._withdrawals_service.reject_withdrawal(
                withdrawal_id=withdrawal_id,
                reason=reason,
            )
        elif name == "get_withdrawals_statistics":
            return await self._withdrawals_service.get_statistics()
        return {"error": "Unknown withdrawals tool"}

    async def _execute_system_tool(self, name: str, inp: dict) -> Any:
        """Execute system administration tools."""
        from app.services.ai_system_service import AISystemService
        system_service = AISystemService(self.session, self.admin_data)

        if name == "get_emergency_status":
            return await system_service.get_emergency_status()
        elif name == "emergency_full_stop":
            return await system_service.emergency_full_stop()
        elif name == "emergency_full_resume":
            return await system_service.emergency_full_resume()
        elif name == "toggle_emergency_deposits":
            return await system_service.toggle_emergency_deposits(enable_stop=inp["enable_stop"])
        elif name == "toggle_emergency_withdrawals":
            return await system_service.toggle_emergency_withdrawals(enable_stop=inp["enable_stop"])
        elif name == "toggle_emergency_roi":
            return await system_service.toggle_emergency_roi(enable_stop=inp["enable_stop"])
        elif name == "get_blockchain_status":
            return await system_service.get_blockchain_status()
        elif name == "switch_rpc_provider":
            return await system_service.switch_rpc_provider(provider=inp["provider"])
        elif name == "toggle_rpc_auto_switch":
            return await system_service.toggle_rpc_auto_switch(enable=inp["enable"])
        elif name == "get_platform_health":
            return await system_service.get_platform_health()
        elif name == "get_global_settings":
            return await system_service.get_global_settings()
        return {"error": "Unknown system tool"}

    async def _execute_admin_mgmt_tool(self, name: str, inp: dict) -> Any:
        """Execute admin management tools."""
        from app.services.ai_admin_management_service import AIAdminManagementService
        admin_mgmt_service = AIAdminManagementService(self.session, self.admin_data)

        if name == "get_admins_list":
            return await admin_mgmt_service.get_admins_list()
        elif name == "get_admin_details":
            return await admin_mgmt_service.get_admin_details(admin_identifier=inp["admin_identifier"])
        elif name == "block_admin":
            return await admin_mgmt_service.block_admin(
                admin_identifier=inp["admin_identifier"],
                reason=inp["reason"],
            )
        elif name == "unblock_admin":
            return await admin_mgmt_service.unblock_admin(admin_identifier=inp["admin_identifier"])
        elif name == "change_admin_role":
            return await admin_mgmt_service.change_admin_role(
                admin_identifier=inp["admin_identifier"],
                new_role=inp["new_role"],
            )
        elif name == "get_admin_stats":
            return await admin_mgmt_service.get_admin_stats()
        return {"error": "Unknown admin management tool"}

    async def _execute_deposits_tool(self, name: str, inp: dict) -> Any:
        """Execute deposits tools."""
        if name == "get_deposit_levels_config":
            return await self._deposits_service.get_deposit_levels_config()
        elif name == "get_user_deposits_list":
            user_id = validate_user_identifier(inp.get("user_identifier"))
            return await self._deposits_service.get_user_deposits(user_identifier=user_id)
        elif name == "get_pending_deposits":
            limit = validate_limit(inp.get("limit"), default=20, max_limit=100)
            return await self._deposits_service.get_pending_deposits(limit=limit)
        elif name == "get_deposit_details":
            deposit_id = validate_positive_int(inp.get("deposit_id"), "deposit_id")
            return await self._deposits_service.get_deposit_details(deposit_id=deposit_id)
        elif name == "get_platform_deposit_stats":
            return await self._deposits_service.get_platform_deposit_stats()
        elif name == "change_max_deposit_level":
            new_max = validate_positive_int(inp.get("new_max"), "new_max", max_value=10)
            return await self._deposits_service.change_max_deposit_level(new_max=new_max)
        elif name == "create_manual_deposit":
            user_id = validate_user_identifier(inp.get("user_identifier"))
            level = validate_positive_int(inp.get("level"), "level", max_value=10)
            amount = validate_positive_decimal(inp.get("amount"), "amount")
            reason = validate_required_string(inp.get("reason"), "reason", max_length=500)
            return await self._deposits_service.create_manual_deposit(
                user_identifier=user_id,
                level=level,
                amount=amount,
                reason=reason,
            )
        elif name == "modify_deposit_roi":
            deposit_id = validate_positive_int(inp.get("deposit_id"), "deposit_id")
            reason = validate_required_string(inp.get("reason"), "reason", max_length=500)
            # These are optional, but validate if provided
            new_roi_paid = None
            new_roi_cap = None
            if inp.get("new_roi_paid") is not None:
                new_roi_paid = validate_positive_decimal(inp.get("new_roi_paid"), "new_roi_paid")
            if inp.get("new_roi_cap") is not None:
                new_roi_cap = validate_positive_decimal(inp.get("new_roi_cap"), "new_roi_cap")
            return await self._deposits_service.modify_deposit_roi(
                deposit_id=deposit_id,
                new_roi_paid=new_roi_paid,
                new_roi_cap=new_roi_cap,
                reason=reason,
            )
        elif name == "cancel_deposit":
            deposit_id = validate_positive_int(inp.get("deposit_id"), "deposit_id")
            reason = validate_required_string(inp.get("reason"), "reason", max_length=500)
            return await self._deposits_service.cancel_deposit(
                deposit_id=deposit_id,
                reason=reason,
            )
        elif name == "confirm_deposit":
            deposit_id = validate_positive_int(inp.get("deposit_id"), "deposit_id")
            reason = validate_optional_string(inp.get("reason"), "reason", max_length=500) or ""
            return await self._deposits_service.confirm_deposit(
                deposit_id=deposit_id,
                reason=reason,
            )
        return {"error": "Unknown deposits tool"}

    async def _execute_roi_tool(self, name: str, inp: dict) -> Any:
        """Execute ROI corridor tools."""
        if name == "get_roi_config":
            return await self._roi_service.get_roi_config(level=inp.get("level"))
        elif name == "set_roi_corridor":
            return await self._roi_service.set_roi_corridor(
                level=inp["level"],
                mode=inp["mode"],
                roi_min=inp.get("roi_min"),
                roi_max=inp.get("roi_max"),
                roi_fixed=inp.get("roi_fixed"),
                reason=inp.get("reason", ""),
            )
        elif name == "get_corridor_history":
            return await self._roi_service.get_corridor_history(
                level=inp.get("level"),
                limit=inp.get("limit", 20),
            )
        return {"error": "Unknown ROI tool"}

    async def _execute_blacklist_tool(self, name: str, inp: dict) -> Any:
        """Execute blacklist tools."""
        if name == "get_blacklist":
            return await self._blacklist_service.get_blacklist(limit=inp.get("limit", 50))
        elif name == "check_blacklist":
            return await self._blacklist_service.check_blacklist(identifier=inp["identifier"])
        elif name == "add_to_blacklist":
            return await self._blacklist_service.add_to_blacklist(
                identifier=inp["identifier"],
                reason=inp["reason"],
                action_type=inp.get("action_type", "pre_block"),
            )
        elif name == "remove_from_blacklist":
            return await self._blacklist_service.remove_from_blacklist(
                identifier=inp["identifier"],
                reason=inp["reason"],
            )
        return {"error": "Unknown blacklist tool"}

    async def _execute_finpass_tool(self, name: str, inp: dict) -> Any:
        """Execute finpass recovery tools."""
        if name == "get_finpass_requests":
            return await self._finpass_service.get_pending_requests(limit=inp.get("limit", 20))
        elif name == "get_finpass_request_details":
            return await self._finpass_service.get_request_details(request_id=inp["request_id"])
        elif name == "approve_finpass_request":
            return await self._finpass_service.approve_request(
                request_id=inp["request_id"],
                notes=inp.get("notes", ""),
            )
        elif name == "reject_finpass_request":
            return await self._finpass_service.reject_request(
                request_id=inp["request_id"],
                reason=inp["reason"],
            )
        elif name == "get_finpass_stats":
            return await self._finpass_service.get_finpass_stats()
        return {"error": "Unknown finpass tool"}

    async def _execute_wallet_tool(self, name: str, inp: dict) -> Any:
        """Execute wallet tools."""
        from app.services.ai_wallet_service import AIWalletService
        wallet_service = AIWalletService(self.session, self.admin_data)

        if name == "check_user_wallet":
            return await wallet_service.check_user_wallet(user_identifier=inp["user_identifier"])
        elif name == "get_plex_rate":
            return await wallet_service.get_plex_rate()
        elif name == "get_wallet_summary_for_dialog":
            return await wallet_service.get_wallet_summary_for_dialog_end(
                user_telegram_id=inp["user_telegram_id"]
            )
        return {"error": "Unknown wallet tool"}

    async def _execute_referral_tool(self, name: str, inp: dict) -> Any:
        """Execute referral tools."""
        if name == "get_platform_referral_stats":
            return await self._referral_service.get_platform_referral_stats()
        elif name == "get_user_referrals":
            return await self._referral_service.get_user_referrals(
                user_identifier=inp["user_identifier"],
                limit=inp.get("limit", 20),
            )
        elif name == "get_top_referrers":
            return await self._referral_service.get_top_referrers(limit=inp.get("limit", 20))
        elif name == "get_top_earners":
            return await self._referral_service.get_top_earners(limit=inp.get("limit", 20))
        return {"error": "Unknown referral tool"}

    async def _execute_logs_tool(self, name: str, inp: dict) -> Any:
        """Execute logs tools."""
        if name == "get_recent_logs":
            return await self._logs_service.get_recent_logs(
                limit=inp.get("limit", 30),
                action_type=inp.get("action_type"),
            )
        elif name == "get_admin_activity":
            return await self._logs_service.get_admin_activity(
                admin_identifier=inp["admin_identifier"],
                limit=inp.get("limit", 30),
            )
        elif name == "search_logs":
            return await self._logs_service.search_logs(
                user_id=inp.get("user_id"),
                action_type=inp.get("action_type"),
                limit=inp.get("limit", 30),
            )
        elif name == "get_action_types_stats":
            return await self._logs_service.get_action_types_stats()
        return {"error": "Unknown logs tool"}

    async def _execute_settings_tool(self, name: str, inp: dict) -> Any:
        """Execute settings tools."""
        if name == "get_withdrawal_settings":
            return await self._settings_service.get_withdrawal_settings()
        elif name == "set_min_withdrawal":
            return await self._settings_service.set_min_withdrawal(amount=Decimal(str(inp["amount"])))
        elif name == "toggle_daily_limit":
            return await self._settings_service.toggle_daily_limit(enabled=inp["enabled"])
        elif name == "set_daily_limit":
            return await self._settings_service.set_daily_limit(amount=Decimal(str(inp["amount"])))
        elif name == "toggle_auto_withdrawal":
            return await self._settings_service.toggle_auto_withdrawal(enabled=inp["enabled"])
        elif name == "set_service_fee":
            return await self._settings_service.set_service_fee(fee=Decimal(str(inp["fee"])))
        elif name == "get_deposit_settings":
            return await self._settings_service.get_deposit_settings()
        elif name == "set_level_corridor":
            return await self._settings_service.set_level_corridor(
                level_type=inp["level_type"],
                min_amount=Decimal(str(inp["min_amount"])),
                max_amount=Decimal(str(inp["max_amount"])),
            )
        elif name == "toggle_deposit_level":
            return await self._settings_service.toggle_deposit_level(
                level_type=inp["level_type"],
                enabled=inp["enabled"],
            )
        elif name == "set_plex_rate":
            return await self._settings_service.set_plex_rate(rate=Decimal(str(inp["rate"])))
        elif name == "get_scheduled_tasks":
            return await self._settings_service.get_scheduled_tasks()
        elif name == "trigger_task":
            return await self._settings_service.trigger_task(task_id=inp["task_id"])
        elif name == "create_admin":
            return await self._settings_service.create_admin(
                telegram_id=inp["telegram_id"],
                username=inp.get("username"),
                role=inp["role"],
            )
        elif name == "delete_admin":
            return await self._settings_service.delete_admin(telegram_id=inp["telegram_id"])
        return {"error": "Unknown settings tool"}

    async def _execute_security_tool(self, name: str, inp: dict) -> Any:
        """Execute security tools."""
        from app.services.admin_security_service import (
            VERIFIED_ADMIN_IDS,
            AdminSecurityService,
            username_similarity,
        )

        security_service = AdminSecurityService(self.session)

        if name == "check_username_spoofing":
            username = inp["username"].lstrip("@")
            telegram_id = inp.get("telegram_id", 0)

            warnings = []
            for admin_id, admin_info in VERIFIED_ADMIN_IDS.items():
                if admin_id == telegram_id:
                    continue
                sim = username_similarity(username, admin_info["username"])
                if sim >= 0.7:
                    level = "🚨 КРИТИЧНО" if sim >= 0.9 else "⚠️ ПОДОЗРЕНИЕ"
                    warnings.append(
                        f"{level}: @{username} похож на админа "
                        f"@{admin_info['username']} ({sim * 100:.0f}%)"
                    )

            if warnings:
                return (
                    f"🔍 **Проверка безопасности: @{username}**\n\n"
                    + "\n".join(warnings)
                    + "\n\n⚠️ Возможная попытка маскировки под админа!"
                )
            return f"✅ @{username} не похож ни на одного верифицированного админа"

        elif name == "get_verified_admins":
            admins = await security_service.get_all_verified_admins()
            lines = ["🛡️ **Верифицированные администраторы:**\n"]
            for a in admins:
                lines.append(
                    f"• {a['username']} (ID: `{a['telegram_id']}`)\n"
                    f"  Роль: {a['role']}, Имя: {a['name']}"
                )
            return "\n".join(lines)

        elif name == "verify_admin_identity":
            telegram_id = inp["telegram_id"]
            username = inp.get("username")

            verification = await security_service.verify_admin_identity(telegram_id, username)

            if verification["is_verified_admin"]:
                info = verification["admin_info"]
                result = (
                    f"✅ **ВЕРИФИЦИРОВАН**\n\n"
                    f"Telegram ID: `{info['telegram_id']}`\n"
                    f"Username: @{info['expected_username']}\n"
                    f"Роль: {info['role']}\n"
                    f"Имя: {info['name']}"
                )
                if verification["warnings"]:
                    result += "\n\n⚠️ Предупреждения:\n" + "\n".join(verification["warnings"])
                return result
            else:
                if verification["spoofing_detected"]:
                    return (
                        f"🚨 **ВНИМАНИЕ! ПОПЫТКА СПУФИНГА!**\n\n"
                        f"Telegram ID: `{telegram_id}`\n"
                        f"Username: @{username}\n\n"
                        f"Похож на админа: @{verification['similar_to_admin']}\n\n"
                        f"{verification['warnings'][0] if verification['warnings'] else ''}"
                    )
                return f"❌ ID `{telegram_id}` НЕ является верифицированным админом"

        return {"error": "Unknown security tool"}
