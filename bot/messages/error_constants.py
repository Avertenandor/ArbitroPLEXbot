"""
Error Message Constants.

Short, frequently used error messages for handlers.
For detailed error templates see error_messages.py
"""

# ========================================================================
# USER ERROR CONSTANTS (Russian)
# ========================================================================

# User errors
ERROR_USER_NOT_FOUND = "❌ Ошибка: пользователь не найден"
ERROR_USER_NOT_FOUND_TRY_START = (
    "❌ Ошибка: пользователь не найден. Попробуйте /start"
)

# System errors
ERROR_SYSTEM = "❌ Системная ошибка"
ERROR_SYSTEM_DOT = "❌ Системная ошибка."
ERROR_SYSTEM_TRY_START = (
    "❌ Системная ошибка. Отправьте /start или попробуйте позже."
)
ERROR_SYSTEM_NO_SESSION = "❌ Системная ошибка (no session factory)"

# Data errors
ERROR_DATA_LOST = "❌ Ошибка: данные потеряны"
ERROR_SESSION_DATA_LOST = "❌ Ошибка: данные сессии потеряны."
ERROR_CONTEXT_LOST = "❌ Ошибка контекста пользователя. Повторите /start"

# ID not found errors
ERROR_REQUEST_ID_NOT_FOUND = "❌ Ошибка: ID запроса не найден."
ERROR_REQUEST_ID_LOST = "❌ Ошибка: ID запроса потерян."
ERROR_APPEAL_ID_NOT_FOUND = "❌ Ошибка: ID заявки не найден."
ERROR_TICKET_ID_NOT_FOUND = (
    "❌ Ошибка: ID обращения не найден. Вернитесь к списку."
)
ERROR_USER_ID_NOT_FOUND = "❌ Ошибка: не удалось определить пользователя"
ERROR_USER_ID_LOST = "❌ Ошибка: ID пользователя потерян."
ERROR_RECORD_ID_LOST = "❌ Ошибка: ID записи потерян."
ERROR_DIALOG_NOT_FOUND = "❌ Ошибка: диалог не найден."
ERROR_DIALOG_CLOSED = "❌ Ошибка: диалог не найден или закрыт."

# Wallet errors
ERROR_WALLET_NOT_FOUND = "❌ Кошелек не найден"
ERROR_WALLET_VALIDATION = (
    "❌ Ошибка валидации контрольной суммы адреса."
)

# Access errors
ERROR_ACCESS_DENIED = "❌ Ошибка: доступ запрещен"
ERROR_INVALID_FORMAT = "❌ Ошибка: неверный формат запроса"

# Loading errors
ERROR_LOADING = "❌ Ошибка загрузки"
ERROR_LOADING_DATA = "❌ Ошибка загрузки данных"
ERROR_LOADING_REQUEST = (
    "❌ Произошла ошибка при загрузке данных запроса.\n"
)
ERROR_LOADING_STATS = (
    "❌ Произошла ошибка при загрузке статистики. Попробуйте позже."
)

# Update errors
ERROR_UPDATE = "❌ Ошибка"
ERROR_UPDATE_STATUS = "❌ Ошибка при обновлении статуса"
ERROR_UPDATE_BALANCE = "❌ Ошибка обновления"

# Generic errors
ERROR_GENERIC = "❌ Ошибка"
ERROR_OCCURRED = "❌ Произошла ошибка"
ERROR_TRY_LATER = "❌ Произошла ошибка. Попробуйте позже."
ERROR_UNKNOWN = "❌ Неизвестная ошибка"

# ========================================================================
# ADMIN ERROR CONSTANTS
# ========================================================================

ERROR_ADMIN_DELETE = "❌ Ошибка при удалении админа"
ERROR_ADMIN_CREATE = "❌ Ошибка при создании админа"
ERROR_ADMIN_ID_NOT_FOUND = "❌ Ошибка: admin_id не найден"

# ========================================================================
# SPECIFIC OPERATION ERRORS
# ========================================================================

ERROR_REPORT_GENERATION = (
    "❌ Произошла ошибка при генерации отчета. "
    "Обратитесь в поддержку."
)
ERROR_WITHDRAWAL_PROCESSING = (
    "❌ Произошла ошибка при обработке заявки"
)
ERROR_PASSWORD_RETRIEVAL = (
    "❌ Ошибка при получении пароля. Обратитесь в поддержку."
)

# ========================================================================
# COMMON SUFFIXES
# ========================================================================

SUFFIX_TRY_LATER = "Попробуйте позже."
SUFFIX_CONTACT_SUPPORT = "Обратитесь в поддержку."
SUFFIX_TRY_START = "Отправьте /start или попробуйте позже."
