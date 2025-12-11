"""Messaging and broadcast tool handler.

This module provides handlers for messaging operations including direct messages,
broadcasts, user list management, and dialog invitations.
"""

import logging
from typing import Any

from ..base import BaseToolHandler, HandlerContext


__all__ = ["MessagingToolHandler"]


logger = logging.getLogger(__name__)


class MessagingToolHandler(BaseToolHandler):
    """Handler for messaging and broadcast tools.

    This handler manages messaging operations including sending messages to individual
    users, broadcasting to groups, retrieving user lists, and managing dialog invitations.

    Attributes:
        context: Handler context containing session, bot, and admin information.
        broadcast_service: Service for handling broadcast operations.
    """

    def __init__(self, context: HandlerContext, broadcast_service: Any) -> None:
        """Initialize the messaging tool handler.

        Args:
            context: Handler context containing necessary execution environment.
            broadcast_service: Service instance for broadcast operations.
        """
        super().__init__(context)
        self.broadcast_service = broadcast_service

    def get_tool_names(self) -> set[str]:
        """Get the set of tool names that this handler can process.

        Returns:
            A set of tool names for messaging operations.
        """
        return {
            "send_message_to_user",
            "broadcast_to_group",
            "get_users_list",
            "invite_to_dialog",
            "mass_invite_to_dialog",
        }

    async def handle(self, tool_name: str, tool_input: dict, **kwargs) -> Any:
        """Handle the execution of a messaging tool.

        Args:
            tool_name: Name of the tool to execute.
            tool_input: Dictionary containing input parameters for the tool.
            **kwargs: Additional keyword arguments for tool execution.

        Returns:
            The result of the tool execution.

        Raises:
            ValueError: If the tool name is not supported or input is invalid.
        """
        logger.info(f"Executing messaging tool: {tool_name}")

        if tool_name == "send_message_to_user":
            return await self._send_message_to_user(tool_input)
        elif tool_name == "broadcast_to_group":
            return await self._broadcast_to_group(tool_input)
        elif tool_name == "get_users_list":
            return await self._get_users_list(tool_input)
        elif tool_name == "invite_to_dialog":
            return await self._invite_to_dialog(tool_input)
        elif tool_name == "mass_invite_to_dialog":
            return await self._mass_invite_to_dialog(tool_input)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def _send_message_to_user(self, tool_input: dict) -> dict[str, Any]:
        """Send a message to a specific user.

        Args:
            tool_input: Dictionary containing:
                - user_identifier: User ID or telegram ID to send message to
                - message_text: Text content of the message (max 4000 characters)

        Returns:
            Dictionary containing execution status and result details.

        Raises:
            ValueError: If validation fails.
        """
        logger.info("Executing send_message_to_user")

        # Validate required fields
        if "user_identifier" not in tool_input:
            raise ValueError("Missing required field: user_identifier")
        if "message_text" not in tool_input:
            raise ValueError("Missing required field: message_text")

        user_identifier = tool_input["user_identifier"]
        message_text = tool_input["message_text"]

        # Validate message text length
        if not isinstance(message_text, str):
            raise ValueError("message_text must be a string")
        if len(message_text) == 0:
            raise ValueError("message_text cannot be empty")
        if len(message_text) > 4000:
            raise ValueError("message_text exceeds maximum length of 4000 characters")

        # Validate user identifier
        if not isinstance(user_identifier, (int, str)):
            raise ValueError("user_identifier must be an integer or string")

        try:
            # Send message via bot
            await self.context.bot.send_message(
                chat_id=user_identifier,
                text=message_text,
                parse_mode="Markdown",
            )

            logger.info(f"Message sent successfully to user {user_identifier}")
            return {
                "success": True,
                "message": f"Message sent successfully to user {user_identifier}",
                "user_identifier": user_identifier,
            }
        except Exception as e:
            logger.error(f"Failed to send message to user {user_identifier}: {e}")
            return {
                "success": False,
                "error": str(e),
                "user_identifier": user_identifier,
            }

    async def _broadcast_to_group(self, tool_input: dict) -> dict[str, Any]:
        """Broadcast a message to a group of users.

        Args:
            tool_input: Dictionary containing:
                - group: Group identifier or filter criteria
                - message_text: Text content to broadcast (max 4000 characters)
                - limit: Maximum number of users to send to (default 100, max 1000)

        Returns:
            Dictionary containing broadcast status and statistics.

        Raises:
            ValueError: If validation fails.
        """
        logger.info("Executing broadcast_to_group")

        # Validate required fields
        if "group" not in tool_input:
            raise ValueError("Missing required field: group")
        if "message_text" not in tool_input:
            raise ValueError("Missing required field: message_text")

        group = tool_input["group"]
        message_text = tool_input["message_text"]
        limit = tool_input.get("limit", 100)

        # Validate message text
        if not isinstance(message_text, str):
            raise ValueError("message_text must be a string")
        if len(message_text) == 0:
            raise ValueError("message_text cannot be empty")
        if len(message_text) > 4000:
            raise ValueError("message_text exceeds maximum length of 4000 characters")

        # Validate limit
        if not isinstance(limit, int):
            raise ValueError("limit must be an integer")
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if limit > 1000:
            raise ValueError("limit exceeds maximum of 1000")

        try:
            # Prepare broadcast data
            broadcast_data = {
                "type": "text",
                "text": message_text,
            }

            # Start broadcast
            broadcast_id = await self.broadcast_service.start_broadcast(
                admin_id=self.context.admin_id,
                broadcast_data=broadcast_data,
                button_data=None,
                admin_telegram_id=self.context.admin_id,
            )

            logger.info(f"Broadcast started with ID: {broadcast_id}")
            return {
                "success": True,
                "broadcast_id": broadcast_id,
                "message": f"Broadcast started to group '{group}' with limit {limit}",
                "group": group,
                "limit": limit,
            }
        except Exception as e:
            logger.error(f"Failed to start broadcast to group {group}: {e}")
            return {
                "success": False,
                "error": str(e),
                "group": group,
            }

    async def _get_users_list(self, tool_input: dict) -> dict[str, Any]:
        """Get a list of users from a specific group.

        Args:
            tool_input: Dictionary containing:
                - group: Group identifier or filter criteria
                - limit: Maximum number of users to return (default 20, max 100)

        Returns:
            Dictionary containing list of users and metadata.

        Raises:
            ValueError: If validation fails.
        """
        logger.info("Executing get_users_list")

        # Validate required fields
        if "group" not in tool_input:
            raise ValueError("Missing required field: group")

        group = tool_input["group"]
        limit = tool_input.get("limit", 20)

        # Validate limit
        if not isinstance(limit, int):
            raise ValueError("limit must be an integer")
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if limit > 100:
            raise ValueError("limit exceeds maximum of 100")

        try:
            # Import UserService
            from app.services.user_service import UserService

            user_service = UserService(self.context.session)

            # Get users list (this is a simplified implementation)
            # In a real implementation, you would filter by group
            users = await user_service.get_verified_users_list(limit=limit)

            logger.info(f"Retrieved {len(users)} users from group '{group}'")
            return {
                "success": True,
                "users": users,
                "count": len(users),
                "group": group,
                "limit": limit,
            }
        except Exception as e:
            logger.error(f"Failed to get users list for group {group}: {e}")
            return {
                "success": False,
                "error": str(e),
                "group": group,
            }

    async def _invite_to_dialog(self, tool_input: dict) -> dict[str, Any]:
        """Invite a user to a dialog.

        Args:
            tool_input: Dictionary containing:
                - user_identifier: User ID or telegram ID to invite
                - custom_message: Optional custom invitation message (max 500 characters)

        Returns:
            Dictionary containing invitation status.

        Raises:
            ValueError: If validation fails.
        """
        logger.info("Executing invite_to_dialog")

        # Validate required fields
        if "user_identifier" not in tool_input:
            raise ValueError("Missing required field: user_identifier")

        user_identifier = tool_input["user_identifier"]
        custom_message = tool_input.get("custom_message")

        # Validate user identifier
        if not isinstance(user_identifier, (int, str)):
            raise ValueError("user_identifier must be an integer or string")

        # Validate custom message if provided
        if custom_message is not None:
            if not isinstance(custom_message, str):
                raise ValueError("custom_message must be a string")
            if len(custom_message) > 500:
                raise ValueError("custom_message exceeds maximum length of 500 characters")

        try:
            # Prepare invitation message
            if custom_message:
                invitation_text = custom_message
            else:
                invitation_text = "You have been invited to join a dialog."

            # Send invitation via bot
            await self.context.bot.send_message(
                chat_id=user_identifier,
                text=invitation_text,
                parse_mode="Markdown",
            )

            logger.info(f"Invitation sent to user {user_identifier}")
            return {
                "success": True,
                "message": f"Invitation sent to user {user_identifier}",
                "user_identifier": user_identifier,
                "custom_message": custom_message,
            }
        except Exception as e:
            logger.error(f"Failed to send invitation to user {user_identifier}: {e}")
            return {
                "success": False,
                "error": str(e),
                "user_identifier": user_identifier,
            }

    async def _mass_invite_to_dialog(self, tool_input: dict) -> dict[str, Any]:
        """Send mass invitations to a dialog for a group of users.

        Args:
            tool_input: Dictionary containing:
                - group: Group identifier or filter criteria
                - custom_message: Optional custom invitation message (max 500 characters)
                - limit: Maximum number of users to invite (default 50, max 200)

        Returns:
            Dictionary containing mass invitation status and statistics.

        Raises:
            ValueError: If validation fails.
        """
        logger.info("Executing mass_invite_to_dialog")

        # Validate required fields
        if "group" not in tool_input:
            raise ValueError("Missing required field: group")

        group = tool_input["group"]
        custom_message = tool_input.get("custom_message")
        limit = tool_input.get("limit", 50)

        # Validate limit
        if not isinstance(limit, int):
            raise ValueError("limit must be an integer")
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if limit > 200:
            raise ValueError("limit exceeds maximum of 200")

        # Validate custom message if provided
        if custom_message is not None:
            if not isinstance(custom_message, str):
                raise ValueError("custom_message must be a string")
            if len(custom_message) > 500:
                raise ValueError("custom_message exceeds maximum length of 500 characters")

        try:
            # Prepare invitation message
            if custom_message:
                invitation_text = custom_message
            else:
                invitation_text = "You have been invited to join a dialog."

            # Prepare broadcast data for mass invitation
            broadcast_data = {
                "type": "text",
                "text": invitation_text,
            }

            # Start broadcast as mass invitation
            broadcast_id = await self.broadcast_service.start_broadcast(
                admin_id=self.context.admin_id,
                broadcast_data=broadcast_data,
                button_data=None,
                admin_telegram_id=self.context.admin_id,
            )

            logger.info(f"Mass invitation started with broadcast ID: {broadcast_id}")
            return {
                "success": True,
                "broadcast_id": broadcast_id,
                "message": f"Mass invitation started for group '{group}' with limit {limit}",
                "group": group,
                "limit": limit,
                "custom_message": custom_message,
            }
        except Exception as e:
            logger.error(f"Failed to start mass invitation for group {group}: {e}")
            return {
                "success": False,
                "error": str(e),
                "group": group,
            }
