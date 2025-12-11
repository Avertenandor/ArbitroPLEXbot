"""System administration tool handler.

This module provides the SystemToolHandler class for managing system-level operations
in the AI assistant, including emergency stops, RPC provider switching, global settings
management, and platform health monitoring.
"""

import logging
from typing import Any

from app.services.ai_system_service import AISystemService

from ..base import BaseToolHandler, HandlerContext

__all__ = ["SystemToolHandler"]

logger = logging.getLogger(__name__)


class SystemToolHandler(BaseToolHandler):
    """Handler for system administration tools.

    This handler manages all system-level operations including:
    - Emergency stop controls (deposits, withdrawals, ROI)
    - RPC provider management and switching
    - Global settings retrieval
    - Platform health monitoring

    Note: SystemToolHandler creates AISystemService on-demand for each operation.

    Attributes:
        context: Handler context containing session, bot, and admin information.
    """

    def __init__(self, context: HandlerContext) -> None:
        """Initialize the system tool handler.

        Args:
            context: Handler context containing necessary execution environment.
        """
        super().__init__(context)

    def get_tool_names(self) -> set[str]:
        """Get the set of tool names that this handler can process.

        Returns:
            A set containing all system administration tool names.
        """
        return {
            "get_emergency_status",
            "emergency_full_stop",
            "emergency_full_resume",
            "toggle_emergency_deposits",
            "toggle_emergency_withdrawals",
            "toggle_emergency_roi",
            "get_blockchain_status",
            "switch_rpc_provider",
            "toggle_rpc_auto_switch",
            "get_platform_health",
            "get_global_settings",
        }

    async def handle(self, tool_name: str, tool_input: dict, **kwargs) -> Any:
        """Handle the execution of a specific system administration tool.

        Args:
            tool_name: Name of the tool to execute.
            tool_input: Dictionary containing input parameters for the tool.
            **kwargs: Additional keyword arguments for tool execution.

        Returns:
            The result of the tool execution.

        Raises:
            ValueError: If the tool name is unknown or input validation fails.
        """
        logger.info(f"Executing system administration tool: {tool_name}")

        if tool_name == "get_emergency_status":
            return await self._get_emergency_status(tool_input)
        elif tool_name == "emergency_full_stop":
            return await self._emergency_full_stop(tool_input)
        elif tool_name == "emergency_full_resume":
            return await self._emergency_full_resume(tool_input)
        elif tool_name == "toggle_emergency_deposits":
            return await self._toggle_emergency_deposits(tool_input)
        elif tool_name == "toggle_emergency_withdrawals":
            return await self._toggle_emergency_withdrawals(tool_input)
        elif tool_name == "toggle_emergency_roi":
            return await self._toggle_emergency_roi(tool_input)
        elif tool_name == "get_blockchain_status":
            return await self._get_blockchain_status(tool_input)
        elif tool_name == "switch_rpc_provider":
            return await self._switch_rpc_provider(tool_input)
        elif tool_name == "toggle_rpc_auto_switch":
            return await self._toggle_rpc_auto_switch(tool_input)
        elif tool_name == "get_platform_health":
            return await self._get_platform_health(tool_input)
        elif tool_name == "get_global_settings":
            return await self._get_global_settings(tool_input)
        else:
            raise ValueError(f"Unknown system administration tool: {tool_name}")

    def _create_system_service(self) -> AISystemService:
        """Create AISystemService instance on-demand.

        Returns:
            Configured AISystemService instance.
        """
        return AISystemService(self.context.session, self.context.admin_data)

    async def _get_emergency_status(self, tool_input: dict) -> dict[str, Any]:
        """Get current emergency stop status.

        Args:
            tool_input: Dictionary (no parameters required).

        Returns:
            Current status of all emergency flags.
        """
        logger.debug("Getting emergency status")

        system_service = self._create_system_service()
        result = await system_service.get_emergency_status()

        logger.info(f"Emergency status retrieved: {result.get('success', False)}")
        return result

    async def _emergency_full_stop(self, tool_input: dict) -> dict[str, Any]:
        """Execute full emergency stop of all financial operations.

        Args:
            tool_input: Dictionary (no parameters required).

        Returns:
            Result of emergency full stop operation.
        """
        logger.debug("Executing emergency full stop")

        system_service = self._create_system_service()
        result = await system_service.emergency_full_stop()

        if result.get("success"):
            logger.critical(f"EMERGENCY FULL STOP activated by admin {self.context.admin_id}")
        else:
            logger.warning(f"Emergency full stop failed: {result.get('error')}")

        return result

    async def _emergency_full_resume(self, tool_input: dict) -> dict[str, Any]:
        """Resume all financial operations.

        Args:
            tool_input: Dictionary (no parameters required).

        Returns:
            Result of emergency full resume operation.
        """
        logger.debug("Executing emergency full resume")

        system_service = self._create_system_service()
        result = await system_service.emergency_full_resume()

        if result.get("success"):
            logger.warning(f"All operations RESUMED by admin {self.context.admin_id}")
        else:
            logger.warning(f"Emergency full resume failed: {result.get('error')}")

        return result

    async def _toggle_emergency_deposits(self, tool_input: dict) -> dict[str, Any]:
        """Toggle emergency stop for deposits.

        Args:
            tool_input: Dictionary containing enable_stop (bool, required).

        Returns:
            Result of toggle operation.
        """
        logger.debug("Toggling emergency deposits")

        enable_stop = tool_input.get("enable_stop")
        if enable_stop is None:
            return {"success": False, "error": "❌ Параметр enable_stop обязателен"}

        if not isinstance(enable_stop, bool):
            return {"success": False, "error": "❌ Параметр enable_stop должен быть boolean"}

        system_service = self._create_system_service()
        result = await system_service.toggle_emergency_deposits(enable_stop)

        if result.get("success"):
            action = "STOPPED" if enable_stop else "RESUMED"
            logger.warning(f"Emergency deposits {action} by admin {self.context.admin_id}")
        else:
            logger.warning(f"Toggle emergency deposits failed: {result.get('error')}")

        return result

    async def _toggle_emergency_withdrawals(self, tool_input: dict) -> dict[str, Any]:
        """Toggle emergency stop for withdrawals.

        Args:
            tool_input: Dictionary containing enable_stop (bool, required).

        Returns:
            Result of toggle operation.
        """
        logger.debug("Toggling emergency withdrawals")

        enable_stop = tool_input.get("enable_stop")
        if enable_stop is None:
            return {"success": False, "error": "❌ Параметр enable_stop обязателен"}

        if not isinstance(enable_stop, bool):
            return {"success": False, "error": "❌ Параметр enable_stop должен быть boolean"}

        system_service = self._create_system_service()
        result = await system_service.toggle_emergency_withdrawals(enable_stop)

        if result.get("success"):
            action = "STOPPED" if enable_stop else "RESUMED"
            logger.warning(f"Emergency withdrawals {action} by admin {self.context.admin_id}")
        else:
            logger.warning(f"Toggle emergency withdrawals failed: {result.get('error')}")

        return result

    async def _toggle_emergency_roi(self, tool_input: dict) -> dict[str, Any]:
        """Toggle emergency stop for ROI accruals.

        Args:
            tool_input: Dictionary containing enable_stop (bool, required).

        Returns:
            Result of toggle operation.
        """
        logger.debug("Toggling emergency ROI")

        enable_stop = tool_input.get("enable_stop")
        if enable_stop is None:
            return {"success": False, "error": "❌ Параметр enable_stop обязателен"}

        if not isinstance(enable_stop, bool):
            return {"success": False, "error": "❌ Параметр enable_stop должен быть boolean"}

        system_service = self._create_system_service()
        result = await system_service.toggle_emergency_roi(enable_stop)

        if result.get("success"):
            action = "STOPPED" if enable_stop else "RESUMED"
            logger.warning(f"Emergency ROI {action} by admin {self.context.admin_id}")
        else:
            logger.warning(f"Toggle emergency ROI failed: {result.get('error')}")

        return result

    async def _get_blockchain_status(self, tool_input: dict) -> dict[str, Any]:
        """Get current blockchain/RPC status.

        Args:
            tool_input: Dictionary (no parameters required).

        Returns:
            RPC providers status information.
        """
        logger.debug("Getting blockchain status")

        system_service = self._create_system_service()
        result = await system_service.get_blockchain_status()

        logger.info(f"Blockchain status retrieved: {result.get('success', False)}")
        return result

    async def _switch_rpc_provider(self, tool_input: dict) -> dict[str, Any]:
        """Switch active RPC provider.

        Args:
            tool_input: Dictionary containing provider (str, required).
                Valid values: quicknode, nodereal, nodereal2

        Returns:
            Result of provider switch operation.
        """
        logger.debug("Switching RPC provider")

        provider = tool_input.get("provider")
        if not provider:
            return {"success": False, "error": "❌ Параметр provider обязателен"}

        if not isinstance(provider, str):
            return {"success": False, "error": "❌ Параметр provider должен быть строкой"}

        system_service = self._create_system_service()
        result = await system_service.switch_rpc_provider(provider)

        if result.get("success"):
            logger.info(f"RPC provider switched to {provider.upper()} by admin {self.context.admin_id}")
        else:
            logger.warning(f"RPC provider switch failed: {result.get('error')}")

        return result

    async def _toggle_rpc_auto_switch(self, tool_input: dict) -> dict[str, Any]:
        """Toggle auto-switching of RPC providers.

        Args:
            tool_input: Dictionary containing enable (bool, required).

        Returns:
            Result of toggle operation.
        """
        logger.debug("Toggling RPC auto-switch")

        enable = tool_input.get("enable")
        if enable is None:
            return {"success": False, "error": "❌ Параметр enable обязателен"}

        if not isinstance(enable, bool):
            return {"success": False, "error": "❌ Параметр enable должен быть boolean"}

        system_service = self._create_system_service()
        result = await system_service.toggle_rpc_auto_switch(enable)

        if result.get("success"):
            status = "ENABLED" if enable else "DISABLED"
            logger.info(f"RPC auto-switch {status} by admin {self.context.admin_id}")
        else:
            logger.warning(f"Toggle RPC auto-switch failed: {result.get('error')}")

        return result

    async def _get_platform_health(self, tool_input: dict) -> dict[str, Any]:
        """Get comprehensive platform health status.

        Args:
            tool_input: Dictionary (no parameters required).

        Returns:
            Health metrics for all platform components.
        """
        logger.debug("Getting platform health")

        system_service = self._create_system_service()
        result = await system_service.get_platform_health()

        logger.info(f"Platform health retrieved: {result.get('overall', 'Unknown')}")
        return result

    async def _get_global_settings(self, tool_input: dict) -> dict[str, Any]:
        """Get current global platform settings.

        Args:
            tool_input: Dictionary (no parameters required).

        Returns:
            All global platform settings.
        """
        logger.debug("Getting global settings")

        system_service = self._create_system_service()
        result = await system_service.get_global_settings()

        logger.info(f"Global settings retrieved: {result.get('success', False)}")
        return result
