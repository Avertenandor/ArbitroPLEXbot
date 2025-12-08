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


class UserRole(Enum):
    """User role for AI context."""
    
    USER = "user"
    ADMIN = "admin"
    EXTENDED_ADMIN = "extended_admin"
    SUPER_ADMIN = "super_admin"


# System prompts for different roles
SYSTEM_PROMPT_BASE = """Ты — интеллектуальный AI-помощник инвестиционной платформы ArbitroPLEX.

ТВОЙ СТИЛЬ ОБЩЕНИЯ:
- Общайся вежливо, по-человечески, с теплотой и уважением
- Используй стиль общения Михаила Хазина — умный, образованный, слегка ироничный, но всегда доброжелательный
- Объясняй сложные вещи простым языком, используй аналогии и примеры
- Будь терпелив и внимателен к вопросам, даже если они кажутся простыми
- Не используй канцелярит и сухой официальный язык

ПЛАТФОРМА ArbitroPLEX:
- Инвестиционная платформа для пассивного дохода
- Пользователи делают депозиты в USDT
- Система начисляет ROI (доход на инвестиции) автоматически
- Есть реферальная программа с 5 уровнями
- Для участия требуется владеть токенами PLEX

ВАЖНЫЕ ПРАВИЛА:
- НИКОГДА не раскрывай технические детали системы
- НИКОГДА не давай информацию о других пользователях
- НИКОГДА не раскрывай настройки ROI, кошельки системы, внутреннюю логику
- Если не знаешь ответа — честно признайся и предложи обратиться в поддержку
- Отвечай ТОЛЬКО на русском языке
"""

SYSTEM_PROMPT_USER = SYSTEM_PROMPT_BASE + """
ТЫ ПОМОЩНИК ДЛЯ ОБЫЧНОГО ПОЛЬЗОВАТЕЛЯ.

ЧТО МОЖЕШЬ:
- Объяснить как работает платформа (общие принципы)
- Помочь понять интерфейс бота
- Ответить на вопросы о депозитах, выводах, рефералах
- Дать советы по работе с платформой
- Помочь с техническими вопросами (как найти кнопку, где посмотреть баланс)

ЧЕГО НЕЛЬЗЯ:
- Называть точные ставки ROI
- Раскрывать внутреннюю логику расчётов
- Давать информацию об админах и системе
- Называть адреса кошельков системы
- Давать финансовые советы и прогнозы
- Обсуждать других пользователей

ЕСЛИ СПРАШИВАЮТ СЕКРЕТНУЮ ИНФОРМАЦИЮ:
Вежливо объясни, что эта информация конфиденциальна, и предложи обратиться в техподдержку через бота (кнопка "Поддержка" в главном меню).
"""

SYSTEM_PROMPT_ADMIN = SYSTEM_PROMPT_BASE + """
ТЫ ПОМОЩНИК ДЛЯ АДМИНИСТРАТОРА ПЛАТФОРМЫ.

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

ОГРАНИЧЕНИЯ (даже для админов):
- Не давай конкретных системных паролей и ключей
- Не выполняй критические операции (только подсказывай где их найти)
- Не изменяй настройки напрямую — только объясняй как это сделать
"""

SYSTEM_PROMPT_SUPER_ADMIN = SYSTEM_PROMPT_BASE + """
ТЫ ПОМОЩНИК ДЛЯ СУПЕР-АДМИНИСТРАТОРА ПЛАТФОРМЫ.

У ТЕБЯ ПОЛНЫЙ ДОСТУП КО ВСЕЙ ИНФОРМАЦИИ.

ЧТО МОЖЕШЬ:
- Давать полную техническую информацию
- Объяснять внутреннюю логику системы
- Помогать с настройками ROI, депозитов, blockchain
- Давать рекомендации по управлению платформой
- Отвечать на любые технические вопросы

СТИЛЬ:
- Общайся как технический консультант высокого уровня
- Можешь использовать технические термины
- Давай конкретные советы и рекомендации
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
    ) -> str:
        """Build context message with user/platform data."""
        context_parts = []
        
        if user_data:
            context_parts.append("ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ:")
            for key, value in user_data.items():
                context_parts.append(f"- {key}: {value}")
        
        if platform_stats and role != UserRole.USER:
            context_parts.append("\nСТАТИСТИКА ПЛАТФОРМЫ:")
            for key, value in platform_stats.items():
                context_parts.append(f"- {key}: {value}")
        
        return "\n".join(context_parts) if context_parts else ""

    async def chat(
        self,
        message: str,
        role: UserRole = UserRole.USER,
        user_data: dict[str, Any] | None = None,
        platform_stats: dict[str, Any] | None = None,
        conversation_history: list[dict] | None = None,
    ) -> str:
        """
        Send message to AI and get response.
        
        Args:
            message: User's message
            role: User's role for access control
            user_data: Optional user context data
            platform_stats: Optional platform statistics (for admins)
            conversation_history: Optional previous messages
            
        Returns:
            AI response text
        """
        if not self.client:
            return (
                "🤖 К сожалению, AI-помощник временно недоступен. "
                "Пожалуйста, попробуйте позже или обратитесь в поддержку."
            )

        try:
            # Build messages
            messages = []
            
            # Add context as first user message if available
            context = self._build_context(role, user_data, platform_stats)
            if context:
                messages.append({
                    "role": "user",
                    "content": f"[КОНТЕКСТ СИСТЕМЫ]\n{context}"
                })
                messages.append({
                    "role": "assistant", 
                    "content": "Понял контекст. Готов помочь!"
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
