"""
Formatters utility.

Utility functions for formatting data in the app layer.
"""


def format_user_identifier(user) -> str:
    """
    Format user as @username or ID:telegram_id.

    Args:
        user: Object with username and telegram_id attributes

    Returns:
        Formatted string like "@username" or "ID:123456"
    """
    if hasattr(user, 'username') and user.username:
        return f"@{user.username}"
    if hasattr(user, 'telegram_id'):
        return f"ID:{user.telegram_id}"
    return "Unknown"


def escape_md(text: str | None) -> str:
    """
    Escape special characters for Markdown V1.

    Escapes: _ * ` [

    Args:
        text: Input text

    Returns:
        Escaped text safe for Markdown
    """
    if not text:
        return ""
    return str(text).replace("_", "\\_").replace("*", "\\*").replace("`", "\\`").replace("[", "\\[")
