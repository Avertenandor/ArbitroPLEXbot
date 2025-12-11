"""
Admin Management Tool Handler.

Handles admin user management operations.
"""

import logging
from typing import Any

from ..base import BaseToolHandler, HandlerContext

logger = logging.getLogger(__name__)

__all__ = ["AdminMgmtToolHandler"]


class AdminMgmtToolHandler(BaseToolHandler):
    """Handler for admin management tools."""

    def __init__(self, context: HandlerContext) -> None:
        """Initialize handler with context."""
        super().__init__(context)

    def get_tool_names(self) -> set[str]:
        """Return supported tool names."""
        return {
            "get_admins_list",
            "get_admin_details",
            "block_admin",
            "unblock_admin",
            "change_admin_role",
            "get_admin_stats",
        }

    async def handle(self, tool_name: str, tool_input: dict[str, Any], **kwargs) -> Any:
        """Execute admin management tool."""
        logger.info(f"Executing admin management tool: {tool_name} by admin {self.context.admin_id}")

        # Create service on-demand
        from app.services.ai_admin_management_service import AIAdminManagementService
        service = AIAdminManagementService(self.context.session, self.context.admin_data)

        if tool_name == "get_admins_list":
            return await service.get_admins_list()

        elif tool_name == "get_admin_details":
            return await service.get_admin_details(
                admin_identifier=tool_input["admin_identifier"]
            )

        elif tool_name == "block_admin":
            return await service.block_admin(
                admin_identifier=tool_input["admin_identifier"],
                reason=tool_input["reason"],
            )

        elif tool_name == "unblock_admin":
            return await service.unblock_admin(
                admin_identifier=tool_input["admin_identifier"]
            )

        elif tool_name == "change_admin_role":
            return await service.change_admin_role(
                admin_identifier=tool_input["admin_identifier"],
                new_role=tool_input["new_role"],
            )

        elif tool_name == "get_admin_stats":
            return await service.get_admin_stats()

        raise ValueError(f"Unknown admin management tool: {tool_name}")
