"""
Message Builder for AI Assistant.

Handles system prompt selection and context building for conversations.
"""

from typing import Any

from loguru import logger

from app.config.security import TECH_DEPUTIES
from app.services.ai import (
    ROLE_DESCRIPTIONS,
    SYSTEM_PROMPT_ADMIN,
    SYSTEM_PROMPT_SUPER_ADMIN,
    SYSTEM_PROMPT_TECH_DEPUTY,
    SYSTEM_PROMPT_USER,
    UserRole,
)


def get_system_prompt(
    role: UserRole,
    username: str | None = None,
    telegram_id: int | None = None,
) -> str:
    """
    Get system prompt based on user role, telegram_id and username.

    Args:
        role: User role
        username: Username (fallback if telegram_id not provided)
        telegram_id: Telegram ID (primary identifier)

    Returns:
        System prompt string
    """
    # SECURITY: Check telegram_id FIRST, then username as fallback
    # Tech deputy ID: 1691026253 (@AI_XAN)
    if telegram_id == 1691026253:
        return SYSTEM_PROMPT_TECH_DEPUTY

    # Fallback to username only if telegram_id not provided
    # (backwards compat)
    if (
        telegram_id is None
        and username
        and username.replace("@", "") in TECH_DEPUTIES
    ):
        logger.warning(
            f"TECH_DEPUTY access by username only: {username}. "
            "This is deprecated - use telegram_id!"
        )
        return SYSTEM_PROMPT_TECH_DEPUTY

    if role == UserRole.SUPER_ADMIN:
        return SYSTEM_PROMPT_SUPER_ADMIN
    elif role in (UserRole.ADMIN, UserRole.EXTENDED_ADMIN):
        return SYSTEM_PROMPT_ADMIN
    else:
        return SYSTEM_PROMPT_USER


def build_context(
    role: UserRole,
    user_data: dict[str, Any] | None = None,
    platform_stats: dict[str, Any] | None = None,
    monitoring_data: str | None = None,
) -> str:
    """
    Build context message with user/platform data.

    Args:
        role: User role
        user_data: User information
        platform_stats: Platform statistics
        monitoring_data: Monitoring data (for admins)

    Returns:
        Formatted context string
    """
    context_parts = []

    # Role identification (critical for AI to know who it's talking to)
    role_desc = ROLE_DESCRIPTIONS.get(role, "пользователь")
    context_parts.append(f"[РОЛЬ СОБЕСЕДНИКА: {role_desc.upper()}]")
    context_parts.append("")

    if user_data:
        context_parts.append("ИНФОРМАЦИЯ О СОБЕСЕДНИКЕ:")
        for key, value in user_data.items():
            context_parts.append(f"- {key}: {value}")
        context_parts.append("")

    # Add knowledge base - USE COMPACT VERSION to save tokens!
    # Full KB = ~9000 tokens, Compact KB = ~1500 tokens (saves 83%)
    try:
        from app.services.knowledge_base import get_knowledge_base

        kb = get_knowledge_base()
        # Use compact version instead of full KB
        kb_context = kb.format_compact()
        if kb_context:
            context_parts.append(kb_context)
            context_parts.append("")
    except Exception as e:
        logger.debug(f"Knowledge base not available: {e}")

    # Add real monitoring data for admins (but limit size)
    if monitoring_data and role != UserRole.USER:
        # Truncate monitoring data to save tokens
        if len(monitoring_data) > 2000:
            monitoring_data = (
                monitoring_data[:2000] + "\n... (сокращено для экономии)"
            )
        context_parts.append(monitoring_data)
        context_parts.append("")

    if platform_stats and role != UserRole.USER:
        context_parts.append("ДОПОЛНИТЕЛЬНАЯ СТАТИСТИКА:")
        for key, value in platform_stats.items():
            context_parts.append(f"- {key}: {value}")

    return "\n".join(context_parts) if context_parts else ""
