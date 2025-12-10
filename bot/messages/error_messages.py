"""
Error Message Templates.

Russian messages for users, English for admin logs.
Provides friendly error messages without technical details for users.
"""

import traceback

from loguru import logger


# ============================================================================
# USER ERROR MESSAGES (Russian)
# ============================================================================

DATABASE_ERROR = (
    "❌ <b>Ошибка базы данных</b>\n\n"
    "Возникла временная проблема с базой данных.\n"
    "Администраторы уже уведомлены.\n\n"
    "Пожалуйста, попробуйте позже."
)

NETWORK_ERROR = (
    "❌ <b>Ошибка сети</b>\n\n"
    "Не удалось установить соединение.\n"
    "Проверьте подключение к интернету и попробуйте снова.\n\n"
    "Если проблема не исчезнет, обратитесь в поддержку."
)

BLOCKCHAIN_ERROR = (
    "❌ <b>Ошибка блокчейна</b>\n\n"
    "Не удалось выполнить операцию в блокчейне.\n"
    "Сеть TON может быть временно недоступна.\n\n"
    "Пожалуйста, попробуйте через несколько минут."
)

VALIDATION_ERROR = (
    "❌ <b>Ошибка проверки данных</b>\n\n"
    "Введенные данные некорректны.\n"
    "Пожалуйста, проверьте правильность ввода и попробуйте снова."
)

RATE_LIMIT_ERROR = (
    "⏱ <b>Слишком много запросов</b>\n\n"
    "Вы отправили слишком много запросов за короткое время.\n"
    "Пожалуйста, подождите немного перед следующей попыткой.\n\n"
    "⏳ Попробуйте через 1-2 минуты."
)

PERMISSION_DENIED = (
    "🔒 <b>Доступ запрещен</b>\n\n"
    "У вас нет прав для выполнения этого действия.\n\n"
    "Если вы считаете, что это ошибка, обратитесь к администратору."
)

SESSION_EXPIRED = (
    "⏰ <b>Сессия истекла</b>\n\n"
    "Ваша сессия устарела.\n"
    "Пожалуйста, начните операцию заново.\n\n"
    "Используйте /start для перезапуска."
)

MAINTENANCE_MODE = (
    "🔧 <b>Технические работы</b>\n\n"
    "Бот временно недоступен из-за технического обслуживания.\n"
    "Мы работаем над улучшением сервиса.\n\n"
    "⏳ Ожидаемое время восстановления: 15-30 минут.\n"
    "Спасибо за понимание!"
)

GENERIC_ERROR = (
    "❌ <b>Произошла ошибка</b>\n\n"
    "Возникла непредвиденная проблема.\n"
    "Администраторы уже уведомлены и работают над решением.\n\n"
    "Пожалуйста, попробуйте позже или обратитесь в поддержку."
)

TRY_AGAIN_LATER = (
    "⏳ <b>Попробуйте позже</b>\n\n"
    "Сервис временно недоступен.\n"
    "Пожалуйста, повторите попытку через несколько минут.\n\n"
    "Если проблема сохраняется, свяжитесь с поддержкой."
)


# ============================================================================
# ERROR TYPE MAPPING
# ============================================================================

ERROR_TYPES = {
    "database": DATABASE_ERROR,
    "network": NETWORK_ERROR,
    "blockchain": BLOCKCHAIN_ERROR,
    "validation": VALIDATION_ERROR,
    "rate_limit": RATE_LIMIT_ERROR,
    "permission": PERMISSION_DENIED,
    "session": SESSION_EXPIRED,
    "maintenance": MAINTENANCE_MODE,
    "generic": GENERIC_ERROR,
    "try_later": TRY_AGAIN_LATER,
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def format_error_for_user(error_type: str, details: str | None = None) -> str:
    """
    Format error message for end user.

    Args:
        error_type: Type of error (database, network, blockchain, etc.)
        details: Optional additional details (will be sanitized)

    Returns:
        Formatted user-friendly error message in Russian

    Example:
        >>> format_error_for_user("database")
        "❌ Ошибка базы данных..."
        >>> format_error_for_user("validation", "Неверный формат адреса")
        "❌ Ошибка проверки данных... Детали: Неверный формат адреса"
    """
    # Get base error message
    base_message = ERROR_TYPES.get(error_type, GENERIC_ERROR)

    # Add sanitized details if provided
    if details:
        # Remove technical information from details
        sanitized_details = _sanitize_details(details)
        if sanitized_details:
            base_message += f"\n\n<i>Детали:</i> {sanitized_details}"

    return base_message


def format_error_for_admin(error: Exception, user_id: int, context: str | None = None) -> str:
    """
    Format detailed error message for admin notification.

    Args:
        error: The exception that occurred
        user_id: Telegram user ID who encountered the error
        context: Optional context information (handler name, operation, etc.)

    Returns:
        Formatted admin error message with technical details in English

    Example:
        >>> format_error_for_admin(ValueError("Invalid input"), 123456, "start_handler")
        "🚨 **CRITICAL ERROR**\\n\\n👤 User ID: 123456\\n..."
    """
    # Get exception details
    exception_name = type(error).__name__
    exception_message = str(error)[:300]  # Limit message length

    # Get traceback (last 1000 chars)
    try:
        error_trace = traceback.format_exc()[-1000:]
    except Exception:
        error_trace = "Traceback not available"

    # Build admin message
    admin_message = (
        f"🚨 **CRITICAL ERROR**\n\n"
        f"👤 User ID: `{user_id}`\n"
        f"❌ Exception: `{exception_name}`\n"
    )

    # Add context if provided
    if context:
        admin_message += f"📍 Context: `{context}`\n"

    admin_message += (
        f"📝 Message: `{exception_message}`\n\n"
        f"**Traceback:**\n"
        f"```\n{error_trace}\n```"
    )

    # Log the error for internal tracking
    logger.error(
        "Error formatted for admin notification",
        extra={
            "user_id": user_id,
            "exception_type": exception_name,
            "exception_message": exception_message,
            "context": context,
        },
    )

    return admin_message[:4096]  # Telegram message limit


def _sanitize_details(details: str) -> str:
    """
    Remove technical/sensitive information from error details.

    Args:
        details: Raw error details string

    Returns:
        Sanitized string safe to show to users
    """
    # List of technical terms to filter out
    sensitive_terms = [
        "traceback",
        "exception",
        "stack",
        "file",
        "line",
        "function",
        "module",
        "class",
        ".py",
        "error:",
        "warning:",
    ]

    # Convert to lowercase for checking
    details_lower = details.lower()

    # Check if details contain sensitive information
    for term in sensitive_terms:
        if term in details_lower:
            logger.debug(f"Filtered sensitive term '{term}' from user error message")
            return ""  # Don't show details if they contain technical info

    # Limit length
    return details[:200]


# ============================================================================
# EXCEPTION TYPE DETECTION
# ============================================================================


def detect_error_type(error: Exception) -> str:
    """
    Automatically detect error type from exception.

    Args:
        error: The exception to analyze

    Returns:
        Error type string for format_error_for_user()

    Example:
        >>> from sqlalchemy.exc import DatabaseError
        >>> detect_error_type(DatabaseError())
        "database"
    """
    exception_name = type(error).__name__.lower()

    # Database errors
    if any(
        term in exception_name
        for term in ["database", "operational", "interface", "integrity", "sql"]
    ):
        return "database"

    # Network errors
    if any(
        term in exception_name
        for term in ["network", "connection", "timeout", "http", "request"]
    ):
        return "network"

    # Blockchain errors
    if any(
        term in exception_name for term in ["blockchain", "ton", "web3", "contract"]
    ):
        return "blockchain"

    # Validation errors
    if any(term in exception_name for term in ["validation", "value", "type"]):
        return "validation"

    # Rate limit errors
    if any(term in exception_name for term in ["ratelimit", "throttle", "flood"]):
        return "rate_limit"

    # Permission errors
    if any(term in exception_name for term in ["permission", "forbidden", "auth"]):
        return "permission"

    # Default to generic
    return "generic"


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================


def get_user_error_message(
    error: Exception, details: str | None = None
) -> str:
    """
    Get user-friendly error message automatically detecting error type.

    Args:
        error: The exception that occurred
        details: Optional additional details

    Returns:
        Formatted user error message

    Example:
        >>> from sqlalchemy.exc import DatabaseError
        >>> get_user_error_message(DatabaseError("Connection failed"))
        "❌ Ошибка базы данных..."
    """
    error_type = detect_error_type(error)
    return format_error_for_user(error_type, details)
