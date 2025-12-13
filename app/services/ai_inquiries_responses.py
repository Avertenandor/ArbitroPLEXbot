"""
AI Inquiries Response Builders.

Helper functions to build standardized response dictionaries.
Reduces code duplication in service methods.
"""
from typing import Any


def error_response(error_msg: str) -> dict[str, Any]:
    """
    Build error response.

    Args:
        error_msg: Error message

    Returns:
        Error response dict
    """
    return {"success": False, "error": error_msg}


def success_response(
    message: str,
    **data: Any
) -> dict[str, Any]:
    """
    Build success response with data.

    Args:
        message: Success message
        **data: Additional data fields

    Returns:
        Success response dict
    """
    return {
        "success": True,
        "message": message,
        **data
    }


def inquiries_list_response(
    inquiries_list: list[dict[str, Any]],
    counts: dict[str, int],
) -> dict[str, Any]:
    """
    Build inquiries list response.

    Args:
        inquiries_list: List of formatted inquiries
        counts: Status counts dict

    Returns:
        Response dict
    """
    return {
        "success": True,
        "total_count": len(inquiries_list),
        "counts": counts,
        "inquiries": inquiries_list,
        "message": f"📋 Найдено {len(inquiries_list)} обращений"
    }


def empty_inquiries_response(status: str | None) -> dict[str, Any]:
    """
    Build empty inquiries response.

    Args:
        status: Status filter used

    Returns:
        Response dict
    """
    status_text = f" со статусом '{status}'" if status else ""
    return {
        "success": True,
        "inquiries": [],
        "message": f"ℹ️ Обращений{status_text} не найдено"
    }


def inquiry_details_response(
    inquiry_data: dict[str, Any],
    inquiry_id: int,
) -> dict[str, Any]:
    """
    Build inquiry details response.

    Args:
        inquiry_data: Formatted inquiry data
        inquiry_id: Inquiry ID

    Returns:
        Response dict
    """
    return {
        "success": True,
        "inquiry": inquiry_data,
        "message": f"📋 Обращение #{inquiry_id}"
    }


def take_inquiry_response(
    inquiry_id: int,
    user_info: str,
    question_preview: str,
    admin_name: str,
) -> dict[str, Any]:
    """
    Build take inquiry response.

    Args:
        inquiry_id: Inquiry ID
        user_info: Formatted user info
        question_preview: Question preview text
        admin_name: Admin name

    Returns:
        Response dict
    """
    return {
        "success": True,
        "inquiry_id": inquiry_id,
        "user": user_info,
        "question": question_preview,
        "admin": admin_name,
        "message": f"✅ Обращение #{inquiry_id} взято в работу"
    }


def reply_inquiry_response(
    inquiry_id: int,
    user_info: str,
    message_preview: str,
) -> dict[str, Any]:
    """
    Build reply inquiry response.

    Args:
        inquiry_id: Inquiry ID
        user_info: Formatted user info
        message_preview: Message preview

    Returns:
        Response dict
    """
    return {
        "success": True,
        "inquiry_id": inquiry_id,
        "user": user_info,
        "message_sent": message_preview,
        "message": "✅ Ответ отправлен пользователю"
    }


def close_inquiry_response(
    inquiry_id: int,
    user_info: str,
    admin_name: str,
    reason: str | None,
) -> dict[str, Any]:
    """
    Build close inquiry response.

    Args:
        inquiry_id: Inquiry ID
        user_info: Formatted user info
        admin_name: Admin name
        reason: Closing reason

    Returns:
        Response dict
    """
    return {
        "success": True,
        "inquiry_id": inquiry_id,
        "user": user_info,
        "reason": reason,
        "admin": admin_name,
        "message": f"✅ Обращение #{inquiry_id} закрыто"
    }
