"""
Admin Event Monitor - Constants and Enums.

This module contains all enumerations, emoji mappings, and Russian language
names for event categories and priorities.
"""

from enum import StrEnum


class EventCategory(StrEnum):
    """Категории событий для мониторинга."""

    # Финансы
    DEPOSIT = "deposit"  # Депозиты
    WITHDRAWAL = "withdrawal"  # Выводы
    PLEX_PAYMENT = "plex_payment"  # Оплата PLEX
    REFERRAL = "referral"  # Реферальные бонусы

    # Безопасность
    SECURITY = "security"  # Безопасность
    SUSPICIOUS = "suspicious"  # Подозрительная активность
    BLACKLIST = "blacklist"  # Чёрный список

    # Пользователи
    USER_REGISTRATION = "user_registration"  # Регистрация
    USER_VERIFICATION = "user_verification"  # Верификация
    USER_RECOVERY = "user_recovery"  # Восстановление аккаунта

    # Поддержка
    SUPPORT = "support"  # Тикеты поддержки
    INQUIRY = "inquiry"  # Вопросы пользователей
    APPEAL = "appeal"  # Апелляции

    # Система
    SYSTEM = "system"  # Системные события
    ERROR = "error"  # Ошибки
    MAINTENANCE = "maintenance"  # Техобслуживание


class EventPriority(StrEnum):
    """Приоритет события."""

    CRITICAL = "critical"  # 🔴 Критический - требует немедленного внимания
    HIGH = "high"  # 🟠 Высокий - важно, но не срочно
    MEDIUM = "medium"  # 🟡 Средний - обычное уведомление
    LOW = "low"  # 🟢 Низкий - информационное


# Эмодзи для категорий
CATEGORY_EMOJI = {
    EventCategory.DEPOSIT: "💰",
    EventCategory.WITHDRAWAL: "💸",
    EventCategory.PLEX_PAYMENT: "💎",
    EventCategory.REFERRAL: "👥",
    EventCategory.SECURITY: "🔒",
    EventCategory.SUSPICIOUS: "🚨",
    EventCategory.BLACKLIST: "⛔",
    EventCategory.USER_REGISTRATION: "👤",
    EventCategory.USER_VERIFICATION: "✅",
    EventCategory.USER_RECOVERY: "🔄",
    EventCategory.SUPPORT: "🎫",
    EventCategory.INQUIRY: "❓",
    EventCategory.APPEAL: "📝",
    EventCategory.SYSTEM: "⚙️",
    EventCategory.ERROR: "❌",
    EventCategory.MAINTENANCE: "🔧",
}

# Эмодзи для приоритетов
PRIORITY_EMOJI = {
    EventPriority.CRITICAL: "🔴",
    EventPriority.HIGH: "🟠",
    EventPriority.MEDIUM: "🟡",
    EventPriority.LOW: "🟢",
}

# Названия категорий на русском
CATEGORY_NAMES_RU = {
    EventCategory.DEPOSIT: "Депозит",
    EventCategory.WITHDRAWAL: "Вывод средств",
    EventCategory.PLEX_PAYMENT: "Оплата PLEX",
    EventCategory.REFERRAL: "Реферальный бонус",
    EventCategory.SECURITY: "Безопасность",
    EventCategory.SUSPICIOUS: "Подозрительная активность",
    EventCategory.BLACKLIST: "Чёрный список",
    EventCategory.USER_REGISTRATION: "Регистрация",
    EventCategory.USER_VERIFICATION: "Верификация",
    EventCategory.USER_RECOVERY: "Восстановление",
    EventCategory.SUPPORT: "Тикет поддержки",
    EventCategory.INQUIRY: "Вопрос пользователя",
    EventCategory.APPEAL: "Апелляция",
    EventCategory.SYSTEM: "Система",
    EventCategory.ERROR: "Ошибка",
    EventCategory.MAINTENANCE: "Техобслуживание",
}

# Названия приоритетов на русском
PRIORITY_NAMES_RU = {
    EventPriority.CRITICAL: "КРИТИЧЕСКИЙ",
    EventPriority.HIGH: "Высокий",
    EventPriority.MEDIUM: "Средний",
    EventPriority.LOW: "Низкий",
}
