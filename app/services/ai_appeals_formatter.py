"""
AI Appeals Formatter.

Provides formatting utilities for appeals display and messaging.
"""

from datetime import datetime
from typing import Any


def format_appeal_status(status: str) -> str:
    """
    Format appeal status with emoji.

    Args:
        status: Appeal status string

    Returns:
        Formatted status with emoji
    """
    status_map = {
        "pending": "🟡",
        "under_review": "🔵",
        "approved": "✅",
        "rejected": "❌"
    }
    emoji = status_map.get(status, "⚪")
    return f"{emoji} {status}"


def format_appeal_status_detailed(status: str) -> str:
    """
    Format appeal status with detailed description.

    Args:
        status: Appeal status string

    Returns:
        Formatted status with description
    """
    status_map = {
        "pending": "🟡 Ожидает",
        "under_review": "🔵 На рассмотрении",
        "approved": "✅ Одобрено",
        "rejected": "❌ Отклонено"
    }
    return status_map.get(status, status)


def format_date(dt: datetime | None) -> str:
    """
    Format datetime to readable string.

    Args:
        dt: Datetime object

    Returns:
        Formatted date string or "—" if None
    """
    if not dt:
        return "—"
    return dt.strftime("%d.%m.%Y %H:%M")


def format_date_optional(dt: datetime | None) -> str | None:
    """
    Format datetime to readable string or None.

    Args:
        dt: Datetime object

    Returns:
        Formatted date string or None
    """
    if not dt:
        return None
    return dt.strftime("%d.%m.%Y %H:%M")


def format_text_preview(text: str | None, max_length: int = 100) -> str:
    """
    Create preview of text with ellipsis if needed.

    Args:
        text: Text to preview
        max_length: Maximum length before truncation

    Returns:
        Text preview
    """
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    return text[:max_length] + "..."


def format_appeal_list_item(
    appeal: Any,
    user_info: str,
) -> dict[str, Any]:
    """
    Format appeal for list display.

    Args:
        appeal: Appeal model instance
        user_info: Formatted user identifier

    Returns:
        Formatted appeal dict for list
    """
    status = format_appeal_status(appeal.status)
    text_preview = format_text_preview(appeal.appeal_text or "")
    created = format_date(appeal.created_at)
    reviewed_at = format_date_optional(appeal.reviewed_at)

    return {
        "id": appeal.id,
        "user": user_info,
        "user_id": appeal.user_id,
        "status": status,
        "text_preview": text_preview,
        "created": created,
        "reviewed_at": reviewed_at,
    }


def format_appeal_details(
    appeal: Any,
    user_info: str,
    user_telegram_id: int | None,
    reviewer_info: str | None,
) -> dict[str, Any]:
    """
    Format detailed appeal information.

    Args:
        appeal: Appeal model instance
        user_info: Formatted user identifier
        user_telegram_id: User's telegram ID
        reviewer_info: Reviewer identifier (e.g., @username)

    Returns:
        Formatted appeal details dict
    """
    status = format_appeal_status_detailed(appeal.status)
    created = format_date(appeal.created_at)
    reviewed_at = format_date_optional(appeal.reviewed_at)

    return {
        "id": appeal.id,
        "user": user_info,
        "user_id": appeal.user_id,
        "user_telegram_id": user_telegram_id,
        "blacklist_id": appeal.blacklist_id,
        "status": status,
        "text": appeal.appeal_text,
        "created": created,
        "reviewed_by": reviewer_info,
        "reviewed_at": reviewed_at,
        "review_notes": appeal.review_notes,
    }


def format_reply_message(
    appeal_id: int,
    message: str,
    admin_name: str,
) -> str:
    """
    Format reply message to user.

    Args:
        appeal_id: Appeal ID
        message: Message content
        admin_name: Admin identifier (e.g., @username)

    Returns:
        Formatted message with headers and footers
    """
    return (
        f"📬 **Ответ на ваше обращение #{appeal_id}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{message}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"_От: {admin_name}_"
    )


def format_message_preview(message: str, max_length: int = 100) -> str:
    """
    Create preview of message for logging/display.

    Args:
        message: Message text
        max_length: Maximum length

    Returns:
        Message preview
    """
    if len(message) <= max_length:
        return message
    return message[:max_length] + "..."


def format_admin_identifier(
    admin: Any,
    use_telegram_id: bool = True
) -> str:
    """
    Format admin identifier.

    Args:
        admin: Admin model instance
        use_telegram_id: Whether to use telegram_id as fallback

    Returns:
        Formatted admin identifier
    """
    if admin.username:
        return f"@{admin.username}"

    if use_telegram_id and hasattr(admin, 'telegram_id'):
        return str(admin.telegram_id)

    return f"Admin #{admin.id}"


def format_counts_summary(counts: dict[str, int]) -> str:
    """
    Format appeals count summary.

    Args:
        counts: Dict with status counts

    Returns:
        Formatted counts string
    """
    parts = []
    emoji_map = {
        "pending": "🟡",
        "under_review": "🔵",
        "approved": "✅",
        "rejected": "❌"
    }

    for status, count in counts.items():
        if count > 0:
            emoji = emoji_map.get(status, "⚪")
            parts.append(f"{emoji} {count}")

    return " | ".join(parts) if parts else "Нет обращений"
