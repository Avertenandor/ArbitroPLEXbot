"""Security and anti-spoofing tool handler.

This module provides the SecurityToolHandler class for managing security-related operations
in the AI assistant, including username spoofing detection, admin verification, and
verified admin management.
"""

import logging
from typing import Any

from app.services.admin_security_service import (
    VERIFIED_ADMIN_IDS,
    AdminSecurityService,
    username_similarity,
)

from ..base import BaseToolHandler, HandlerContext

__all__ = ["SecurityToolHandler"]

logger = logging.getLogger(__name__)


class SecurityToolHandler(BaseToolHandler):
    """Handler for security and anti-spoofing tools.

    This handler manages all security-related operations including:
    - Username spoofing detection
    - Admin identity verification
    - Verified admins list retrieval

    Attributes:
        context: Handler context containing session, bot, and admin information.
    """

    def __init__(self, context: HandlerContext) -> None:
        """Initialize the security tool handler.

        Args:
            context: Handler context containing necessary execution environment.
        """
        super().__init__(context)

    def get_tool_names(self) -> set[str]:
        """Get the set of tool names that this handler can process.

        Returns:
            A set containing all security tool names.
        """
        return {
            "check_username_spoofing",
            "get_verified_admins",
            "verify_admin_identity",
        }

    async def handle(self, tool_name: str, tool_input: dict, **kwargs) -> Any:
        """Handle the execution of a specific security tool.

        Args:
            tool_name: Name of the tool to execute.
            tool_input: Dictionary containing input parameters for the tool.
            **kwargs: Additional keyword arguments for tool execution.

        Returns:
            The result of the tool execution.

        Raises:
            ValueError: If the tool name is unknown or input validation fails.
        """
        logger.info(f"Executing security tool: {tool_name}")

        if tool_name == "check_username_spoofing":
            return await self._check_username_spoofing(tool_input)
        elif tool_name == "get_verified_admins":
            return await self._get_verified_admins(tool_input)
        elif tool_name == "verify_admin_identity":
            return await self._verify_admin_identity(tool_input)
        else:
            raise ValueError(f"Unknown security tool: {tool_name}")

    async def _check_username_spoofing(self, tool_input: dict) -> str:
        """Check if a username is attempting to spoof a verified admin.

        Args:
            tool_input: Dictionary containing username (required) and optional telegram_id.

        Returns:
            Formatted string with spoofing detection results.
        """
        logger.debug("Checking username for spoofing")

        username = tool_input.get("username")
        if not username:
            return "❌ Ошибка: username обязателен для проверки"

        telegram_id = tool_input.get("telegram_id")

        # Remove @ if present
        username = username.lstrip("@")

        # Check against all verified admin usernames
        warnings = []
        has_warnings = False

        for admin_id, admin_info in VERIFIED_ADMIN_IDS.items():
            # Skip self if telegram_id provided
            if telegram_id and admin_id == telegram_id:
                continue

            admin_username = admin_info["username"]
            similarity = username_similarity(username, admin_username)

            # Check if similarity >= 0.7 (threshold for spoofing)
            if similarity >= 0.7:
                has_warnings = True
                if similarity >= 0.9:
                    warnings.append(
                        f"🚨 КРИТИЧНО: @{username} почти идентичен "
                        f"админу @{admin_username} (сходство: {similarity * 100:.0f}%)"
                    )
                else:
                    warnings.append(
                        f"⚠️ ПОДОЗРЕНИЕ: @{username} похож на "
                        f"админа @{admin_username} (сходство: {similarity * 100:.0f}%)"
                    )

        if has_warnings:
            logger.warning(f"Spoofing check: Username @{username} has similarities with verified admins")
            return "\n".join(warnings)
        else:
            logger.debug(f"Spoofing check: Username @{username} is not similar to verified admins")
            return f"✅ Username @{username} не похож на известных администраторов"

    async def _get_verified_admins(self, tool_input: dict) -> str:
        """Get list of all verified admins.

        Args:
            tool_input: Dictionary (no parameters required).

        Returns:
            Formatted list of verified admins.
        """
        logger.debug("Getting verified admins list")

        security_service = AdminSecurityService(self.context.session)
        admins = await security_service.get_all_verified_admins()

        if not admins:
            return "❌ Не найдено верифицированных администраторов"

        result = "✅ *Верифицированные администраторы:*\n\n"
        for admin in admins:
            result += (
                f"• {admin['username']} (ID: {admin['telegram_id']})\n"
                f"  Роль: {admin['role']}\n"
                f"  Имя: {admin['name']}\n\n"
            )

        logger.info(f"Retrieved {len(admins)} verified admins")
        return result.strip()

    async def _verify_admin_identity(self, tool_input: dict) -> str:
        """Verify admin identity by telegram_id and optional username.

        Args:
            tool_input: Dictionary containing telegram_id (required) and optional username.

        Returns:
            Formatted verification result.
        """
        logger.debug("Verifying admin identity")

        telegram_id = tool_input.get("telegram_id")
        if telegram_id is None:
            return "❌ Ошибка: telegram_id обязателен для верификации"

        # Ensure telegram_id is an integer
        try:
            telegram_id = int(telegram_id)
        except (ValueError, TypeError):
            return f"❌ Ошибка: некорректный telegram_id: {telegram_id}"

        username = tool_input.get("username")
        if username:
            username = username.lstrip("@")

        security_service = AdminSecurityService(self.context.session)
        verification = await security_service.verify_admin_identity(telegram_id, username)

        # Build result message
        if verification["is_verified_admin"]:
            admin_info = verification["admin_info"]
            result = (
                f"✅ *ВЕРИФИЦИРОВАН*\n\n"
                f"Telegram ID: {admin_info['telegram_id']}\n"
                f"Username: @{admin_info['expected_username']}\n"
                f"Роль: {admin_info['role']}\n"
                f"Имя: {admin_info['name']}"
            )

            # Add warnings if any
            if verification["warnings"]:
                result += "\n\n⚠️ *Предупреждения:*\n"
                for warning in verification["warnings"]:
                    result += f"• {warning}\n"

            logger.info(f"Admin verified: {telegram_id} (@{admin_info['expected_username']})")
            return result
        else:
            # Not a verified admin
            result = f"🚨 *НЕ ВЕРИФИЦИРОВАН*\n\nTelegram ID: {telegram_id}"
            if username:
                result += f"\nUsername: @{username}"

            # Check for spoofing
            if verification["spoofing_detected"]:
                result += "\n\n🚨 *ОБНАРУЖЕНА ПОПЫТКА ПОДДЕЛКИ!*\n"
                for warning in verification["warnings"]:
                    result += f"• {warning}\n"
                logger.error(
                    f"SPOOFING DETECTED: User {telegram_id} (@{username}) "
                    f"similar to admin @{verification['similar_to_admin']}"
                )
            else:
                result += "\n\n❌ Данный пользователь не является верифицированным администратором"
                logger.info(f"User {telegram_id} (@{username}) is not a verified admin")

            return result
