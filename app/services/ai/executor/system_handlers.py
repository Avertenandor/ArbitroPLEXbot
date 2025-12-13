"""
System administration handlers for AI tool execution.

Handles system operations, statistics, logs, settings, blacklist, finpass.
"""

from decimal import Decimal
from typing import Any


class SystemHandlersMixin:
    """Mixin for system administration tool handlers."""

    async def _execute_system_tool(self, name: str, inp: dict) -> Any:
        """Execute system administration tools."""
        from app.services.ai_system import AISystemService

        system_service = AISystemService(self.session, self.admin_data)

        if name == "get_emergency_status":
            return await system_service.get_emergency_status()
        elif name == "emergency_full_stop":
            return await system_service.emergency_full_stop()
        elif name == "emergency_full_resume":
            return await system_service.emergency_full_resume()
        elif name == "toggle_emergency_deposits":
            return await system_service.toggle_emergency_deposits(
                enable_stop=inp["enable_stop"]
            )
        elif name == "toggle_emergency_withdrawals":
            return await system_service.toggle_emergency_withdrawals(
                enable_stop=inp["enable_stop"]
            )
        elif name == "toggle_emergency_roi":
            return await system_service.toggle_emergency_roi(
                enable_stop=inp["enable_stop"]
            )
        elif name == "get_blockchain_status":
            return await system_service.get_blockchain_status()
        elif name == "switch_rpc_provider":
            return await system_service.switch_rpc_provider(
                provider=inp["provider"]
            )
        elif name == "toggle_rpc_auto_switch":
            return await system_service.toggle_rpc_auto_switch(
                enable=inp["enable"]
            )
        elif name == "get_platform_health":
            return await system_service.get_platform_health()
        elif name == "get_global_settings":
            return await system_service.get_global_settings()
        return {"error": "Unknown system tool"}

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

    async def _execute_blacklist_tool(self, name: str, inp: dict) -> Any:
        """Execute blacklist tools."""
        if name == "get_blacklist":
            return await self._blacklist_service.get_blacklist(
                limit=inp.get("limit", 50)
            )
        elif name == "check_blacklist":
            return await self._blacklist_service.check_blacklist(
                identifier=inp["identifier"]
            )
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
            return await self._finpass_service.get_pending_requests(
                limit=inp.get("limit", 20)
            )
        elif name == "get_finpass_request_details":
            return await self._finpass_service.get_request_details(
                request_id=inp["request_id"]
            )
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
            return await self._settings_service.set_min_withdrawal(
                amount=Decimal(str(inp["amount"]))
            )
        elif name == "toggle_daily_limit":
            return await self._settings_service.toggle_daily_limit(
                enabled=inp["enabled"]
            )
        elif name == "set_daily_limit":
            return await self._settings_service.set_daily_limit(
                amount=Decimal(str(inp["amount"]))
            )
        elif name == "toggle_auto_withdrawal":
            return await self._settings_service.toggle_auto_withdrawal(
                enabled=inp["enabled"]
            )
        elif name == "set_service_fee":
            return await self._settings_service.set_service_fee(
                fee=Decimal(str(inp["fee"]))
            )
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
            return await self._settings_service.set_plex_rate(
                rate=Decimal(str(inp["rate"]))
            )
        elif name == "get_scheduled_tasks":
            return await self._settings_service.get_scheduled_tasks()
        elif name == "trigger_task":
            return await self._settings_service.trigger_task(
                task_id=inp["task_id"]
            )
        elif name == "create_admin":
            return await self._settings_service.create_admin(
                telegram_id=inp["telegram_id"],
                username=inp.get("username"),
                role=inp["role"],
            )
        elif name == "delete_admin":
            return await self._settings_service.delete_admin(
                telegram_id=inp["telegram_id"]
            )
        return {"error": "Unknown settings tool"}
