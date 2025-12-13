"""
AI Inquiries Formatter.

Provides formatting utilities for user inquiries data presentation.
All formatting functions for inquiries display and messages.
"""
from datetime import datetime
from typing import Any


def format_user_info(user: Any) -> str:
    """
    Format user information for display.

    Args:
        user: User object with username and telegram_id

    Returns:
        Formatted user string
    """
    if not user:
        return "Неизвестен"
    if user.username:
        return f"@{user.username}"
    return f"ID:{user.telegram_id}"


def format_admin_info(admin: Any, admin_id: int | None = None) -> str | None:
    """
    Format admin information for display.

    Args:
        admin: Admin object with username
        admin_id: Admin ID if admin object is None

    Returns:
        Formatted admin string or None
    """
    if not admin:
        if admin_id:
            return f"Admin#{admin_id}"
        return None
    if admin.username:
        return f"@{admin.username}"
    return f"Admin#{admin_id or 'Unknown'}"


def format_status_emoji(status: str, full: bool = False) -> str:
    """
    Format status with emoji.

    Args:
        status: Status string (new, in_progress, closed)
        full: If True, return full text with emoji

    Returns:
        Formatted status string
    """
    if full:
        emoji_map = {
            "new": "🆕 Новое",
            "in_progress": "🔵 В работе",
            "closed": "✅ Закрыто"
        }
        return emoji_map.get(status, status)

    emoji_map = {
        "new": "🆕",
        "in_progress": "🔵",
        "closed": "✅"
    }
    return emoji_map.get(status, "⚪")


def format_datetime(
    dt: datetime | None,
    date_format: str = "%d.%m.%Y %H:%M"
) -> str:
    """
    Format datetime for display.

    Args:
        dt: Datetime object
        date_format: Format string

    Returns:
        Formatted datetime string or placeholder
    """
    if not dt:
        return "—"
    return dt.strftime(date_format)


def format_short_datetime(dt: datetime | None) -> str:
    """
    Format datetime in short format.

    Args:
        dt: Datetime object

    Returns:
        Formatted datetime string (dd.mm HH:MM)
    """
    return format_datetime(dt, "%d.%m %H:%M")


def format_text_preview(text: str | None, max_length: int = 100) -> str:
    """
    Format text with length limit and ellipsis.

    Args:
        text: Text to format
        max_length: Maximum length

    Returns:
        Formatted text with ellipsis if needed
    """
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def format_inquiry_list_item(inquiry: Any) -> dict[str, Any]:
    """
    Format inquiry for list display.

    Args:
        inquiry: UserInquiry object

    Returns:
        Formatted inquiry dict
    """
    user_info = format_user_info(inquiry.user)
    admin_info = format_admin_info(
        inquiry.assigned_admin,
        inquiry.assigned_admin_id
    )
    status_emoji = format_status_emoji(inquiry.status)

    return {
        "id": inquiry.id,
        "user": user_info,
        "user_id": inquiry.user_id,
        "telegram_id": inquiry.telegram_id,
        "status": f"{status_emoji} {inquiry.status}",
        "question_preview": format_text_preview(
            inquiry.initial_question,
            100
        ),
        "assigned_to": admin_info,
        "created": format_datetime(inquiry.created_at),
    }


def format_message_item(message: Any) -> dict[str, Any]:
    """
    Format inquiry message for display.

    Args:
        message: InquiryMessage object

    Returns:
        Formatted message dict
    """
    sender = (
        "👤 Пользователь"
        if message.sender_type == "user"
        else "👨‍💼 Админ"
    )
    text_preview = format_text_preview(message.message_text, 200)
    time_str = format_short_datetime(message.created_at)

    return {
        "sender": sender,
        "text": text_preview,
        "time": time_str,
    }


def format_inquiry_details(inquiry: Any) -> dict[str, Any]:
    """
    Format detailed inquiry information.

    Args:
        inquiry: UserInquiry object with messages

    Returns:
        Formatted inquiry details dict
    """
    user_info = format_user_info(inquiry.user)
    admin_info = format_admin_info(
        inquiry.assigned_admin,
        inquiry.assigned_admin_id
    )
    status_text = format_status_emoji(inquiry.status, full=True)

    # Format messages
    messages_list = [
        format_message_item(msg)
        for msg in (inquiry.messages or [])
    ]

    return {
        "id": inquiry.id,
        "user": user_info,
        "user_id": inquiry.user_id,
        "telegram_id": inquiry.telegram_id,
        "status": status_text,
        "question": inquiry.initial_question,
        "assigned_to": admin_info,
        "created": format_datetime(inquiry.created_at),
        "assigned_at": format_datetime(inquiry.assigned_at),
        "closed_at": format_datetime(inquiry.closed_at),
        "messages_count": len(messages_list),
        "messages": messages_list[-10:],  # Last 10 messages
    }


def format_inquiry_reply(message: str, admin_name: str) -> str:
    """
    Format reply message to user.

    Args:
        message: Reply text
        admin_name: Admin name or username

    Returns:
        Formatted message for Telegram
    """
    return (
        f"📬 **Ответ на ваше обращение**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{message}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"_От: {admin_name}_"
    )


def format_admin_name(admin: Any) -> str:
    """
    Format admin name for display in messages.

    Args:
        admin: Admin object

    Returns:
        Formatted admin name
    """
    if not admin:
        return "Администратор"
    if admin.username:
        return f"@{admin.username}"
    return "Администратор"
