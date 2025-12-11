"""
AI Assistant Helpers.

Utility functions for building messages, parsing responses,
and other common operations used by the AI assistant service.
"""

from typing import Any

from app.services.ai.prompts import AI_NAME


def wrap_system_prompt(prompt: str) -> list[dict[str, Any]]:
    """
    Wrap system prompt with cache control for Anthropic API.
    
    Uses ephemeral caching to improve performance and reduce costs.
    
    Args:
        prompt: The system prompt text
        
    Returns:
        List with system message containing cache_control
    """
    return [
        {
            "type": "text",
            "text": prompt,
            "cache_control": {"type": "ephemeral"},
        }
    ]


def build_messages(
    context: str,
    conversation_history: list[dict[str, str]] | None,
    message: str,
    ai_name: str = AI_NAME,
) -> list[dict[str, Any]]:
    """
    Build message list for API call with context and history.
    
    Args:
        context: User/system context to prepend
        conversation_history: Previous messages in conversation
        message: Current user message
        ai_name: Name of AI assistant
        
    Returns:
        List of messages for API call
    """
    messages = []

    # Add context as first user message if provided
    if context:
        messages.append(
            {
                "role": "user",
                "content": f"[Контекст диалога]\n{context}",
            }
        )
        messages.append(
            {
                "role": "assistant",
                "content": f"Понятно! Я — {ai_name}, готова помочь.",
            }
        )

    # Add conversation history
    if conversation_history:
        for msg in conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

    # Add current message
    messages.append({"role": "user", "content": message})

    return messages


def extract_user_identifiers(data: dict[str, Any]) -> tuple[str | None, int | None]:
    """
    Extract username and telegram_id from various data sources.
    
    Args:
        data: Dictionary containing user data
        
    Returns:
        Tuple of (username, telegram_id)
    """
    username = None
    telegram_id = None

    # Try different keys
    if "username" in data:
        username = data["username"]
        if username and not username.startswith("@"):
            username = f"@{username}"
    elif "user_data" in data and "username" in data["user_data"]:
        username = data["user_data"]["username"]
        if username and not username.startswith("@"):
            username = f"@{username}"

    if "telegram_id" in data:
        telegram_id = data["telegram_id"]
    elif "user_data" in data and "telegram_id" in data["user_data"]:
        telegram_id = data["user_data"]["telegram_id"]

    return username, telegram_id


def create_tool_result(tool_use_id: str, result: str | dict[str, Any]) -> dict[str, Any]:
    """
    Create tool result message for API.
    
    Args:
        tool_use_id: ID of the tool call
        result: Result content (string or dict)
        
    Returns:
        Formatted tool result message
    """
    if isinstance(result, dict):
        content = str(result)
    else:
        content = result

    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content,
    }


def parse_content_block(block: Any) -> dict[str, Any]:
    """
    Parse content block from API response.
    
    Args:
        block: Content block from response
        
    Returns:
        Parsed block data
    """
    if hasattr(block, "type"):
        block_type = block.type
    elif isinstance(block, dict):
        block_type = block.get("type", "unknown")
    else:
        block_type = "unknown"

    result = {"type": block_type}

    if block_type == "text":
        if hasattr(block, "text"):
            result["text"] = block.text
        elif isinstance(block, dict):
            result["text"] = block.get("text", "")
    elif block_type == "tool_use":
        if hasattr(block, "id"):
            result["id"] = block.id
            result["name"] = block.name
            result["input"] = block.input
        elif isinstance(block, dict):
            result["id"] = block.get("id", "")
            result["name"] = block.get("name", "")
            result["input"] = block.get("input", {})

    return result


def get_unavailable_message() -> str:
    """Get standard unavailable message."""
    return (
        f"🤖 К сожалению, {AI_NAME} сейчас недоступна. "
        "Попробуй позже или обратись напрямую к команде."
    )


def format_tool_error(tool_name: str, error: str) -> str:
    """
    Format error message for tool execution failure.
    
    Args:
        tool_name: Name of the tool that failed
        error: Error message
        
    Returns:
        Formatted error string
    """
    return f"❌ Ошибка выполнения {tool_name}: {error}"


def format_tool_success(tool_name: str, result: str) -> str:
    """
    Format success message for tool execution.
    
    Args:
        tool_name: Name of the tool
        result: Result message
        
    Returns:
        Formatted success string
    """
    return f"✅ {tool_name}: {result}"


def is_valid_telegram_id(value: Any) -> bool:
    """
    Check if value is a valid Telegram ID.
    
    Args:
        value: Value to check
        
    Returns:
        True if valid Telegram ID
    """
    if isinstance(value, int):
        return value > 0
    if isinstance(value, str):
        try:
            return int(value) > 0
        except ValueError:
            return False
    return False


def is_valid_username(value: str) -> bool:
    """
    Check if value is a valid Telegram username.
    
    Args:
        value: Value to check
        
    Returns:
        True if valid username format
    """
    if not isinstance(value, str):
        return False
    username = value.lstrip("@")
    if len(username) < 5 or len(username) > 32:
        return False
    # Basic check - alphanumeric and underscore
    return all(c.isalnum() or c == "_" for c in username)


def parse_user_identifier(identifier: str) -> tuple[str | None, int | None]:
    """
    Parse user identifier into username and/or telegram_id.
    
    Args:
        identifier: @username, telegram_id, or ID:xxx format
        
    Returns:
        Tuple of (username, telegram_id) - one or both may be None
    """
    if not identifier:
        return None, None

    identifier = str(identifier).strip()

    # Check for ID:xxx format
    if identifier.upper().startswith("ID:"):
        try:
            telegram_id = int(identifier[3:])
            return None, telegram_id
        except ValueError:
            return None, None

    # Check for @username
    if identifier.startswith("@"):
        return identifier, None

    # Check for numeric telegram_id
    try:
        telegram_id = int(identifier)
        return None, telegram_id
    except ValueError:
        pass

    # Assume it's a username without @
    if is_valid_username(identifier):
        return f"@{identifier}", None

    return None, None
