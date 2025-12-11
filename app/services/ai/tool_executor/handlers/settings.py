"""Settings management tool handler.

This module provides the SettingsToolHandler class for managing system settings operations
in the AI assistant, including withdrawal settings, deposit settings, scheduled tasks, and admin management.
"""

import logging
from decimal import Decimal
from typing import Any

from ..base import BaseToolHandler, HandlerContext
from ..validators import (
    validate_boolean,
    validate_optional_string,
    validate_positive_decimal,
    validate_positive_int,
    validate_required_string,
)

__all__ = ["SettingsToolHandler"]

logger = logging.getLogger(__name__)


class SettingsToolHandler(BaseToolHandler):
    """Handler for system settings management tools.

    This handler manages all settings-related operations including:
    - Withdrawal settings management
    - Deposit settings management
    - PLEX rate configuration
    - Scheduled tasks management
    - Admin user management

    Attributes:
        context: Handler context containing session, bot, and admin information.
        settings_service: Service for executing settings management operations.
    """

    def __init__(self, context: HandlerContext, settings_service: Any) -> None:
        """Initialize the settings tool handler.

        Args:
            context: Handler context containing necessary execution environment.
            settings_service: Service instance for settings management operations.
        """
        super().__init__(context)
        self.settings_service = settings_service

    def get_tool_names(self) -> set[str]:
        """Get the set of tool names that this handler can process.

        Returns:
            A set containing all settings management tool names.
        """
        return {
            "get_withdrawal_settings",
            "set_min_withdrawal",
            "toggle_daily_limit",
            "set_daily_limit",
            "toggle_auto_withdrawal",
            "set_service_fee",
            "get_deposit_settings",
            "set_level_corridor",
            "toggle_deposit_level",
            "set_plex_rate",
            "get_scheduled_tasks",
            "trigger_task",
            "create_admin",
            "delete_admin",
        }

    async def handle(self, tool_name: str, tool_input: dict, **kwargs) -> Any:
        """Handle the execution of a specific settings management tool.

        Args:
            tool_name: Name of the tool to execute.
            tool_input: Dictionary containing input parameters for the tool.
            **kwargs: Additional keyword arguments for tool execution.

        Returns:
            The result of the tool execution.

        Raises:
            ValueError: If the tool name is unknown or input validation fails.
        """
        logger.info(f"Executing settings management tool: {tool_name}")

        if tool_name == "get_withdrawal_settings":
            return await self._get_withdrawal_settings(tool_input)
        elif tool_name == "set_min_withdrawal":
            return await self._set_min_withdrawal(tool_input)
        elif tool_name == "toggle_daily_limit":
            return await self._toggle_daily_limit(tool_input)
        elif tool_name == "set_daily_limit":
            return await self._set_daily_limit(tool_input)
        elif tool_name == "toggle_auto_withdrawal":
            return await self._toggle_auto_withdrawal(tool_input)
        elif tool_name == "set_service_fee":
            return await self._set_service_fee(tool_input)
        elif tool_name == "get_deposit_settings":
            return await self._get_deposit_settings(tool_input)
        elif tool_name == "set_level_corridor":
            return await self._set_level_corridor(tool_input)
        elif tool_name == "toggle_deposit_level":
            return await self._toggle_deposit_level(tool_input)
        elif tool_name == "set_plex_rate":
            return await self._set_plex_rate(tool_input)
        elif tool_name == "get_scheduled_tasks":
            return await self._get_scheduled_tasks(tool_input)
        elif tool_name == "trigger_task":
            return await self._trigger_task(tool_input)
        elif tool_name == "create_admin":
            return await self._create_admin(tool_input)
        elif tool_name == "delete_admin":
            return await self._delete_admin(tool_input)
        else:
            raise ValueError(f"Unknown settings management tool: {tool_name}")

    async def _get_withdrawal_settings(self, tool_input: dict) -> Any:
        """Get current withdrawal settings.

        Args:
            tool_input: Dictionary (no parameters required).

        Returns:
            Current withdrawal settings configuration.
        """
        logger.debug("Getting withdrawal settings")

        return await self.settings_service.get_withdrawal_settings()

    async def _set_min_withdrawal(self, tool_input: dict) -> Any:
        """Set minimum withdrawal amount.

        Args:
            tool_input: Dictionary containing amount.

        Returns:
            Result of setting minimum withdrawal amount.
        """
        logger.debug("Setting minimum withdrawal amount")

        amount = validate_positive_decimal(
            tool_input.get("amount"),
            "amount"
        )

        return await self.settings_service.set_min_withdrawal(
            amount=amount
        )

    async def _toggle_daily_limit(self, tool_input: dict) -> Any:
        """Toggle daily withdrawal limit.

        Args:
            tool_input: Dictionary containing enabled flag.

        Returns:
            Result of toggling daily limit.
        """
        logger.debug("Toggling daily withdrawal limit")

        enabled = validate_boolean(
            tool_input.get("enabled"),
            "enabled"
        )

        return await self.settings_service.toggle_daily_limit(
            enabled=enabled
        )

    async def _set_daily_limit(self, tool_input: dict) -> Any:
        """Set daily withdrawal limit amount.

        Args:
            tool_input: Dictionary containing amount.

        Returns:
            Result of setting daily limit.
        """
        logger.debug("Setting daily withdrawal limit")

        amount = validate_positive_decimal(
            tool_input.get("amount"),
            "amount"
        )

        return await self.settings_service.set_daily_limit(
            amount=amount
        )

    async def _toggle_auto_withdrawal(self, tool_input: dict) -> Any:
        """Toggle automatic withdrawal processing.

        Args:
            tool_input: Dictionary containing enabled flag.

        Returns:
            Result of toggling auto withdrawal.
        """
        logger.debug("Toggling auto withdrawal")

        enabled = validate_boolean(
            tool_input.get("enabled"),
            "enabled"
        )

        return await self.settings_service.toggle_auto_withdrawal(
            enabled=enabled
        )

    async def _set_service_fee(self, tool_input: dict) -> Any:
        """Set service fee percentage.

        Args:
            tool_input: Dictionary containing fee.

        Returns:
            Result of setting service fee.
        """
        logger.debug("Setting service fee")

        fee = validate_positive_decimal(
            tool_input.get("fee"),
            "fee"
        )

        return await self.settings_service.set_service_fee(
            fee=fee
        )

    async def _get_deposit_settings(self, tool_input: dict) -> Any:
        """Get current deposit settings.

        Args:
            tool_input: Dictionary (no parameters required).

        Returns:
            Current deposit settings configuration.
        """
        logger.debug("Getting deposit settings")

        return await self.settings_service.get_deposit_settings()

    async def _set_level_corridor(self, tool_input: dict) -> Any:
        """Set deposit level corridor (min and max amounts).

        Args:
            tool_input: Dictionary containing level_type, min_amount, and max_amount.

        Returns:
            Result of setting level corridor.
        """
        logger.debug("Setting level corridor")

        level_type = validate_required_string(
            tool_input.get("level_type"),
            "level_type",
            max_length=50
        )
        min_amount = validate_positive_decimal(
            tool_input.get("min_amount"),
            "min_amount"
        )
        max_amount = validate_positive_decimal(
            tool_input.get("max_amount"),
            "max_amount"
        )

        # Validate that min_amount is less than max_amount
        if min_amount >= max_amount:
            raise ValueError("min_amount must be less than max_amount")

        return await self.settings_service.set_level_corridor(
            level_type=level_type,
            min_amount=min_amount,
            max_amount=max_amount
        )

    async def _toggle_deposit_level(self, tool_input: dict) -> Any:
        """Toggle deposit level availability.

        Args:
            tool_input: Dictionary containing level_type and enabled flag.

        Returns:
            Result of toggling deposit level.
        """
        logger.debug("Toggling deposit level")

        level_type = validate_required_string(
            tool_input.get("level_type"),
            "level_type",
            max_length=50
        )
        enabled = validate_boolean(
            tool_input.get("enabled"),
            "enabled"
        )

        return await self.settings_service.toggle_deposit_level(
            level_type=level_type,
            enabled=enabled
        )

    async def _set_plex_rate(self, tool_input: dict) -> Any:
        """Set PLEX exchange rate.

        Args:
            tool_input: Dictionary containing rate.

        Returns:
            Result of setting PLEX rate.
        """
        logger.debug("Setting PLEX rate")

        rate = validate_positive_decimal(
            tool_input.get("rate"),
            "rate"
        )

        return await self.settings_service.set_plex_rate(
            rate=rate
        )

    async def _get_scheduled_tasks(self, tool_input: dict) -> Any:
        """Get list of scheduled tasks.

        Args:
            tool_input: Dictionary (no parameters required).

        Returns:
            List of scheduled tasks.
        """
        logger.debug("Getting scheduled tasks")

        return await self.settings_service.get_scheduled_tasks()

    async def _trigger_task(self, tool_input: dict) -> Any:
        """Manually trigger a scheduled task.

        Args:
            tool_input: Dictionary containing task_id.

        Returns:
            Result of triggering task.
        """
        logger.debug("Triggering scheduled task")

        task_id = validate_required_string(
            tool_input.get("task_id"),
            "task_id",
            max_length=100
        )

        return await self.settings_service.trigger_task(
            task_id=task_id
        )

    async def _create_admin(self, tool_input: dict) -> Any:
        """Create a new admin user.

        Args:
            tool_input: Dictionary containing telegram_id, optional username, and role.

        Returns:
            Result of creating admin user.
        """
        logger.debug("Creating admin user")

        telegram_id = validate_positive_int(
            tool_input.get("telegram_id"),
            "telegram_id"
        )
        username = validate_optional_string(
            tool_input.get("username"),
            "username",
            max_length=100
        )
        role = validate_required_string(
            tool_input.get("role"),
            "role",
            max_length=50
        )

        return await self.settings_service.create_admin(
            telegram_id=telegram_id,
            username=username,
            role=role
        )

    async def _delete_admin(self, tool_input: dict) -> Any:
        """Delete an admin user.

        Args:
            tool_input: Dictionary containing telegram_id.

        Returns:
            Result of deleting admin user.
        """
        logger.debug("Deleting admin user")

        telegram_id = validate_positive_int(
            tool_input.get("telegram_id"),
            "telegram_id"
        )

        return await self.settings_service.delete_admin(
            telegram_id=telegram_id
        )
