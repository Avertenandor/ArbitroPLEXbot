"""
Model Selector for AI Assistant.

Chooses optimal model (Haiku vs Sonnet) based on message complexity
to optimize costs.
"""

from loguru import logger

from app.services.ai import UserRole


def select_model(
    message: str,
    role: UserRole,
    model_sonnet: str,
    model_haiku: str,
) -> str:
    """
    Select optimal model based on message complexity.

    Haiku is 12x cheaper ($0.25/$1.25 vs $3/$15 per 1M tokens).
    Use Haiku for simple queries, Sonnet for complex analysis.

    Args:
        message: User message
        role: User role
        model_sonnet: Sonnet model name
        model_haiku: Haiku model name

    Returns:
        Model name to use
    """
    message_lower = message.lower()

    # Complex keywords requiring Sonnet (analytical, strategic, tools)
    complex_keywords = [
        # Tool usage (always Sonnet for reliability)
        "покажи",
        "найди",
        "поиск",
        "создай",
        "измени",
        "удали",
        "отмени",
        "начисли",
        "заблокируй",
        "разблокируй",
        "одобри",
        "отклони",
        "статистик",
        "отчёт",
        "аналитик",
        "анализ",
        # Complex questions
        "почему",
        "объясни подробно",
        "как работает",
        "стратеги",
        "сравни",
        "разница между",
        "плюсы и минусы",
        # Financial analysis
        "депозит",
        "вывод",
        "баланс",
        "roi",
        "доход",
        "прибыль",
        # Admin tools
        "обращени",
        "тикет",
        "пользовател",
        "админ",
        "логи",
        # Security
        "безопасност",
        "верифик",
        "проверь",
        "подозри",
    ]

    # Simple keywords - can use Haiku (greetings, navigation, simple FAQ)
    simple_keywords = [
        "привет",
        "здравствуй",
        "добрый",
        "пока",
        "спасибо",
        "благодар",
        "что такое",
        "как называется",
        "где найти",
        "какая кнопка",
        "помощь",
        "help",
        "старт",
        "start",
        "меню",
        "да",
        "нет",
        "ок",
        "понял",
        "ясно",
        "хорошо",
    ]

    # Check for complex keywords first
    for keyword in complex_keywords:
        if keyword in message_lower:
            logger.debug(
                f"Token economy: Using Sonnet "
                f"(complex keyword: {keyword})"
            )
            return model_sonnet

    # If message is short and simple - use Haiku
    if len(message) < 50 and any(
        kw in message_lower for kw in simple_keywords
    ):
        logger.debug("Token economy: Using Haiku (simple message)")
        return model_haiku

    # Admins get Sonnet by default (they usually need tools)
    if role in (
        UserRole.SUPER_ADMIN,
        UserRole.ADMIN,
        UserRole.EXTENDED_ADMIN,
    ):
        logger.debug("Token economy: Using Sonnet (admin role)")
        return model_sonnet

    # For regular users with medium-length messages - Haiku
    if len(message) < 200 and role == UserRole.USER:
        logger.debug(
            "Token economy: Using Haiku (regular user, short message)"
        )
        return model_haiku

    # Default to Sonnet for safety
    logger.debug("Token economy: Using Sonnet (default)")
    return model_sonnet
