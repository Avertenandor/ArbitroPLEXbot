"""
AI Assistant Module.

Contains all AI assistant related components:
- prompts: System prompts for different user roles
- tool_definitions: Tool definitions for AI assistant
- helpers: Utility functions for message building and parsing
- tool_executor: Tool execution logic (to be added)
"""

from app.services.ai.helpers import (
    build_messages,
    create_tool_result,
    extract_text_from_response,
    extract_user_identifiers,
    format_tool_error,
    format_tool_success,
    get_api_error_message,
    get_unavailable_message,
    is_valid_telegram_id,
    is_valid_username,
    parse_content_block,
    parse_user_identifier,
    wrap_system_prompt,
)
from app.services.ai.prompts import (
    AI_FULL_NAME,
    AI_NAME,
    ROLE_DESCRIPTIONS,
    SYSTEM_PROMPT_ADMIN,
    SYSTEM_PROMPT_BASE,
    SYSTEM_PROMPT_MODERATOR,
    SYSTEM_PROMPT_SUPER_ADMIN,
    SYSTEM_PROMPT_TECH_DEPUTY,
    SYSTEM_PROMPT_USER,
    UserRole,
    get_system_prompt,
)
from app.services.ai.tool_definitions import (
    get_admin_management_tools,
    get_all_admin_tools,
    get_appeals_tools,
    get_blacklist_tools,
    get_bonus_tools,
    get_deposits_tools,
    get_finpass_tools,
    get_inquiries_tools,
    get_interview_tools,
    get_logs_tools,
    get_messaging_tools,
    get_referral_tools,
    get_roi_tools,
    get_security_tools,
    get_settings_tools,
    get_statistics_tools,
    get_system_admin_tools,
    get_user_management_tools,
    get_user_wallet_tools,
    get_wallet_tools,
    get_withdrawals_tools,
)
from app.services.ai.tool_executor import ToolExecutor


__all__ = [
    # Prompts
    "AI_NAME",
    "AI_FULL_NAME",
    "ROLE_DESCRIPTIONS",
    "SYSTEM_PROMPT_ADMIN",
    "SYSTEM_PROMPT_BASE",
    "SYSTEM_PROMPT_MODERATOR",
    "SYSTEM_PROMPT_SUPER_ADMIN",
    "SYSTEM_PROMPT_TECH_DEPUTY",
    "SYSTEM_PROMPT_USER",
    "UserRole",
    "get_system_prompt",
    # Tool definitions
    "get_admin_management_tools",
    "get_all_admin_tools",
    "get_appeals_tools",
    "get_blacklist_tools",
    "get_bonus_tools",
    "get_deposits_tools",
    "get_finpass_tools",
    "get_inquiries_tools",
    "get_interview_tools",
    "get_logs_tools",
    "get_messaging_tools",
    "get_referral_tools",
    "get_roi_tools",
    "get_security_tools",
    "get_settings_tools",
    "get_statistics_tools",
    "get_system_admin_tools",
    "get_user_management_tools",
    "get_user_wallet_tools",
    "get_wallet_tools",
    "get_withdrawals_tools",
    # Helpers
    "build_messages",
    "create_tool_result",
    "extract_text_from_response",
    "extract_user_identifiers",
    "format_tool_error",
    "format_tool_success",
    "get_api_error_message",
    "get_unavailable_message",
    "is_valid_telegram_id",
    "is_valid_username",
    "parse_content_block",
    "parse_user_identifier",
    "wrap_system_prompt",
    # Tool Executor
    "ToolExecutor",
]
