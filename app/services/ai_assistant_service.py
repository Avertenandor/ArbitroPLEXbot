"""
AI Assistant Service.

Provides integration with Anthropic Claude API for intelligent
assistant functionality with role-based access control.

Style: Friendly, human, educational - like Mikhail Khazin.
"""

from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from loguru import logger

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None


# AI Assistant Name
AI_NAME = "ARIA"  # Artificial Reliable Investment Assistant
AI_FULL_NAME = "ARIA — Artificial Reliable Investment Assistant"


class UserRole(Enum):
    """User role for AI context."""

    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    EXTENDED_ADMIN = "extended_admin"
    SUPER_ADMIN = "super_admin"


# Role descriptions for context
ROLE_DESCRIPTIONS = {
    UserRole.USER: "обычный пользователь платформы",
    UserRole.MODERATOR: "модератор платформы",
    UserRole.ADMIN: "администратор платформы",
    UserRole.EXTENDED_ADMIN: "расширенный администратор платформы",
    UserRole.SUPER_ADMIN: "главный администратор и владелец платформы",
}


# System prompts for different roles
SYSTEM_PROMPT_BASE = f"""Ты — {AI_NAME} (Artificial Reliable Investment Assistant).
Ты интеллектуальный AI-помощник инвестиционной платформы ArbitroPLEX.

ТВОЁ ИМЯ: {AI_NAME}
Всегда представляйся как {AI_NAME} при первом сообщении в диалоге.

ТВОЙ СТИЛЬ ОБЩЕНИЯ:
- Общайся вежливо, по-человечески, с теплотой и уважением
- Стиль Михаила Хазина — умный, образованный, слегка ироничный, доброжелательный
- Объясняй сложные вещи простым языком, используй аналогии и примеры
- Будь терпелив и внимателен к вопросам
- Не используй канцелярит и сухой официальный язык
- Можешь использовать лёгкий юмор, но оставайся профессиональным

ПЛАТФОРМА ArbitroPLEX:
- Инвестиционная платформа для пассивного дохода
- Пользователи делают депозиты в USDT
- Система начисляет ROI (доход на инвестиции) автоматически
- Реферальная программа с 5 уровнями
- Для участия требуется владеть токенами PLEX (10 за вход, 10 за каждый $ депозита)

ВАЖНЫЕ ПРАВИЛА:
- Отвечай ТОЛЬКО на русском языке
- Если не знаешь ответа — честно признайся
"""

SYSTEM_PROMPT_USER = SYSTEM_PROMPT_BASE + """

=== ВАЖНО: ТЫ СЕЙЧАС ОБЩАЕШЬСЯ С ОБЫЧНЫМ ПОЛЬЗОВАТЕЛЕМ ===
Это НЕ админ, НЕ модератор, а обычный участник платформы.
Уровень доступа: МИНИМАЛЬНЫЙ. Никакой внутренней информации!

ЧТО МОЖЕШЬ:
- Объяснить как работает платформа (общие принципы)
- Помочь понять интерфейс бота
- Ответить на вопросы о депозитах, выводах, рефералах
- Дать советы по работе с платформой
- Помочь найти нужную кнопку или раздел

СТРОГО ЗАПРЕЩЕНО:
- Называть точные ставки ROI и алгоритмы расчёта
- Раскрывать внутреннюю логику и архитектуру системы
- Давать информацию об админах, модераторах, владельцах
- Называть адреса кошельков системы
- Давать финансовые советы и прогнозы
- Обсуждать других пользователей
- Рассказывать о серверах, базах данных, технологиях

ЕСЛИ СПРАШИВАЮТ СЕКРЕТНУЮ ИНФОРМАЦИЮ:
Вежливо скажи: "Эта информация конфиденциальна. Если у вас важный вопрос — обратитесь в техподдержку через кнопку 'Поддержка' в главном меню."
"""

SYSTEM_PROMPT_ADMIN = SYSTEM_PROMPT_BASE + """

=== ВАЖНО: ТЫ СЕЙЧАС ОБЩАЕШЬСЯ С АДМИНИСТРАТОРОМ ===
Это админ или модератор платформы. НЕ владелец!
Уровень доступа: СРЕДНИЙ. Рабочая информация, но не секреты системы.

У ТЕБЯ ЕСТЬ ДОСТУП К:
- Общей статистике платформы
- Информации о пользователях (количество, активность)
- Описанию функций админ-панели
- Помощь с задачами администрирования

ЧТО МОЖЕШЬ:
- Объяснить функции админ-панели
- Помочь найти нужный раздел
- Описать процессы работы с пользователями
- Ответить на вопросы о выводах, депозитах, блокировках
- Помочь с техническими вопросами бота
- Объяснять как пользоваться инструментами админки

ОГРАНИЧЕНИЯ (даже для админов):
- НЕ давай системных паролей, ключей API, мастер-ключей
- НЕ раскрывай архитектуру серверов и баз данных
- НЕ обсуждай финансовые потоки и балансы системы
- НЕ выполняй критические операции — только подсказывай
"""

SYSTEM_PROMPT_SUPER_ADMIN = SYSTEM_PROMPT_BASE + """

=== ВАЖНО: ТЫ СЕЙЧАС ОБЩАЕШЬСЯ С ВЛАДЕЛЬЦЕМ ПЛАТФОРМЫ ===
Это главный администратор и создатель ArbitroPLEX.
Уровень доступа: МАКСИМАЛЬНЫЙ. Полная информация без ограничений.

Ты можешь обращаться к нему неформально, как к боссу и другу.

У ТЕБЯ ПОЛНЫЙ ДОСТУП:
- Любая техническая информация
- Внутренняя логика и архитектура системы
- Настройки ROI, депозитов, blockchain
- Рекомендации по управлению и развитию
- Любые технические вопросы

ЧТО МОЖЕШЬ:
- Давать полную техническую информацию
- Объяснять внутреннюю логику системы
- Помогать с настройками всех уровней
- Давать стратегические рекомендации
- Обсуждать развитие платформы
- Быть честным советником

СТИЛЬ:
- Общайся как доверенный технический консультант
- Можешь использовать технические термины
- Давай конкретные советы и рекомендации
- Будь проактивным — предлагай улучшения
"""


class AIAssistantService:
    """
    AI Assistant service using Anthropic Claude API.
    
    Provides role-based intelligent assistance with different
    access levels for users, admins and super admins.
    """

    def __init__(self, api_key: str | None = None) -> None:
        """
        Initialize AI assistant.
        
        Args:
            api_key: Anthropic API key
        """
        self.api_key = api_key
        self.client = None
        self.model = "claude-sonnet-4-20250514"  # Latest Claude Sonnet
        
        if api_key and ANTHROPIC_AVAILABLE:
            try:
                self.client = anthropic.Anthropic(api_key=api_key)
                logger.info("AI Assistant initialized with Anthropic API")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")
                self.client = None
        elif not ANTHROPIC_AVAILABLE:
            logger.warning("Anthropic package not installed")
        else:
            logger.warning("No Anthropic API key provided")

    def _get_system_prompt(self, role: UserRole) -> str:
        """Get system prompt based on user role."""
        if role == UserRole.SUPER_ADMIN:
            return SYSTEM_PROMPT_SUPER_ADMIN
        elif role in (UserRole.ADMIN, UserRole.EXTENDED_ADMIN):
            return SYSTEM_PROMPT_ADMIN
        else:
            return SYSTEM_PROMPT_USER

    def _build_context(
        self,
        role: UserRole,
        user_data: dict[str, Any] | None = None,
        platform_stats: dict[str, Any] | None = None,
        monitoring_data: str | None = None,
    ) -> str:
        """Build context message with user/platform data."""
        context_parts = []

        # Role identification (critical for AI to know who it's talking to)
        role_desc = ROLE_DESCRIPTIONS.get(role, "пользователь")
        context_parts.append(f"[РОЛЬ СОБЕСЕДНИКА: {role_desc.upper()}]")
        context_parts.append("")

        if user_data:
            context_parts.append("ИНФОРМАЦИЯ О СОБЕСЕДНИКЕ:")
            for key, value in user_data.items():
                context_parts.append(f"- {key}: {value}")
            context_parts.append("")

        # Add real monitoring data for admins
        if monitoring_data and role != UserRole.USER:
            context_parts.append(monitoring_data)
            context_parts.append("")

        if platform_stats and role != UserRole.USER:
            context_parts.append("ДОПОЛНИТЕЛЬНАЯ СТАТИСТИКА:")
            for key, value in platform_stats.items():
                context_parts.append(f"- {key}: {value}")

        return "\n".join(context_parts) if context_parts else ""

    async def chat(
        self,
        message: str,
        role: UserRole = UserRole.USER,
        user_data: dict[str, Any] | None = None,
        platform_stats: dict[str, Any] | None = None,
        monitoring_data: str | None = None,
        conversation_history: list[dict] | None = None,
    ) -> str:
        """
        Send message to AI and get response.

        Args:
            message: User's message
            role: User's role for access control
            user_data: Optional user context data
            platform_stats: Optional platform statistics (for admins)
            monitoring_data: Real-time monitoring data (formatted text)
            conversation_history: Optional previous messages

        Returns:
            AI response text
        """
        if not self.client:
            return (
                f"🤖 К сожалению, {AI_NAME} временно недоступна. "
                "Пожалуйста, попробуйте позже или обратитесь в поддержку."
            )

        try:
            # Build messages
            messages = []

            # Add context as first user message if available
            context = self._build_context(
                role, user_data, platform_stats, monitoring_data
            )
            if context:
                messages.append({
                    "role": "user",
                    "content": f"[КОНТЕКСТ СИСТЕМЫ]\n{context}"
                })
                messages.append({
                    "role": "assistant",
                    "content": f"Понял. Я {AI_NAME}, готова помочь!"
                })
            
            # Add conversation history
            if conversation_history:
                messages.extend(conversation_history[-10:])  # Last 10 messages
            
            # Add current message
            messages.append({
                "role": "user",
                "content": message
            })

            # Get system prompt
            system_prompt = self._get_system_prompt(role)

            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system_prompt,
                messages=messages,
            )

            # Extract text response
            if response.content and len(response.content) > 0:
                return response.content[0].text
            
            return "🤖 Не удалось получить ответ. Попробуйте переформулировать вопрос."

        except anthropic.APIConnectionError:
            logger.error("Anthropic API connection error")
            return (
                "🤖 Проблема с подключением к AI. "
                "Проверьте интернет-соединение и попробуйте снова."
            )
        except anthropic.RateLimitError:
            logger.error("Anthropic API rate limit exceeded")
            return (
                "🤖 Слишком много запросов. "
                "Пожалуйста, подождите минуту и попробуйте снова."
            )
        except anthropic.APIStatusError as e:
            logger.error(f"Anthropic API error: {e}")
            return (
                "🤖 Ошибка сервиса AI. "
                "Попробуйте позже или обратитесь в поддержку."
            )
        except Exception as e:
            logger.error(f"Unexpected AI error: {e}")
            return (
                "🤖 Произошла непредвиденная ошибка. "
                "Пожалуйста, обратитесь в техподдержку."
            )

    async def get_quick_help(self, topic: str, role: UserRole) -> str:
        """
        Get quick help on a specific topic.
        
        Args:
            topic: Help topic
            role: User role
            
        Returns:
            Help text
        """
        prompts = {
            "deposit": "Объясни кратко как сделать депозит на платформе",
            "withdrawal": "Объясни кратко как вывести средства",
            "referral": "Объясни кратко как работает реферальная программа",
            "bonus": "Объясни кратко как работают бонусы",
            "plex": "Объясни кратко зачем нужны токены PLEX",
            "roi": "Объясни кратко как начисляется доход",
        }
        
        prompt = prompts.get(topic, f"Дай краткую справку по теме: {topic}")
        return await self.chat(prompt, role=role)

    def is_available(self) -> bool:
        """Check if AI service is available."""
        return self.client is not None


# Singleton instance
_ai_service: AIAssistantService | None = None


def get_ai_service() -> AIAssistantService:
    """Get or create AI service singleton."""
    global _ai_service

    if _ai_service is None:
        from app.config.settings import settings
        _ai_service = AIAssistantService(api_key=settings.anthropic_api_key)

    return _ai_service
