"""
AI Assistant Service Core.

Main service class integrating all AI assistant components.
"""

from typing import Any

from loguru import logger

from app.config.operational_constants import AI_MAX_TOKENS_SHORT
from app.services.ai import AI_NAME, UserRole, get_api_error_message

from .knowledge_extractor import (
    extract_knowledge,
    save_learned_knowledge,
)
from .message_builder import build_context, get_system_prompt
from .model_selector import select_model
from .tool_processor import (
    chat_user_with_wallet,
    chat_with_tools,
    resolve_admin_id,
)

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None


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
        # Models: Sonnet for complex, Haiku for simple (12x cheaper!)
        self.model_sonnet = "claude-sonnet-4-20250514"  # Complex tasks
        self.model_haiku = "claude-haiku-4-5-20251001"  # Simple (12x cheaper)
        self.model = self.model_sonnet  # Default

        # Cache for system prompts (reusable across sessions)
        self._cached_system_prompts: dict[str, str] = {}

        if api_key and ANTHROPIC_AVAILABLE:
            try:
                self.client = anthropic.Anthropic(api_key=api_key)
                logger.info(
                    "AI Assistant initialized with Anthropic API"
                )
            except Exception as e:
                logger.error(
                    f"Failed to initialize Anthropic client: {e}"
                )
                self.client = None
        elif not ANTHROPIC_AVAILABLE:
            logger.warning("Anthropic package not installed")
        else:
            logger.warning("No Anthropic API key provided")

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
                "Пожалуйста, попробуйте позже или обратитесь "
                "в поддержку."
            )

        try:
            # Extract username and telegram_id from user_data
            # for access checks
            username = None
            telegram_id = None
            if user_data:
                username = (
                    user_data.get("username") or user_data.get("Имя")
                )
                telegram_id = (
                    user_data.get("ID") or user_data.get("telegram_id")
                )
                if isinstance(telegram_id, str):
                    try:
                        telegram_id = int(telegram_id)
                    except ValueError:
                        telegram_id = None

            # Build messages
            messages = []

            # Add context as first user message if available
            context = build_context(
                role,
                user_data,
                platform_stats,
                monitoring_data,
            )
            if context:
                messages.append(
                    {
                        "role": "user",
                        "content": f"[КОНТЕКСТ СИСТЕМЫ]\n{context}",
                    }
                )
                messages.append(
                    {
                        "role": "assistant",
                        "content": f"Понял. Я {AI_NAME}, готова помочь!",
                    }
                )

            # Add conversation history
            if conversation_history:
                messages.extend(conversation_history[-10:])  # Last 10 messages

            # Add current message
            messages.append({"role": "user", "content": message})

            # Get system prompt (with telegram_id for secure
            # tech deputy check)
            system_prompt = get_system_prompt(role, username, telegram_id)

            # Smart model selection: use Haiku for simple queries
            # (12x cheaper!)
            # Haiku: $0.25/$1.25 per 1M tokens vs Sonnet: $3/$15
            selected_model = select_model(
                message,
                role,
                self.model_sonnet,
                self.model_haiku,
            )

            # Use prompt caching for system prompt
            # (saves 90% on repeated calls)
            # https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
            system_with_cache = [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ]

            # Call Claude API with caching
            response = self.client.messages.create(
                model=selected_model,
                max_tokens=AI_MAX_TOKENS_SHORT,
                system=system_with_cache,
                messages=messages,
            )

            # Extract text response (safely check for text attribute)
            if response.content and len(response.content) > 0:
                first_block = response.content[0]
                if hasattr(first_block, "text") and first_block.text:
                    return first_block.text

            return (
                "🤖 Не удалось получить ответ. "
                "Попробуйте переформулировать вопрос."
            )

        except Exception as e:
            logger.error(f"AI chat error: {type(e).__name__}: {e}")
            return get_api_error_message(e)

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
            "deposit": (
                "Объясни кратко как сделать депозит "
                "на платформе"
            ),
            "withdrawal": "Объясни кратко как вывести средства",
            "referral": (
                "Объясни кратко как работает "
                "реферальная программа"
            ),
            "bonus": "Объясни кратко как работают бонусы",
            "plex": "Объясни кратко зачем нужны токены PLEX",
            "roi": "Объясни кратко как начисляется доход",
        }

        prompt = prompts.get(topic, f"Дай краткую справку по теме: {topic}")
        return await self.chat(prompt, role=role)

    def is_available(self) -> bool:
        """Check if AI service is available."""
        return self.client is not None

    async def extract_knowledge(
        self,
        conversation: list[dict],
        source_user: str,
        source_telegram_id: int | None = None,
    ) -> list[dict] | None:
        """
        Extract knowledge from conversation to add to knowledge base.

        ВАЖНО: Самообучение включено для ВСЕХ админов,
        которые общаются с Арьей в админском режиме.

        Args:
            conversation: List of message dicts with role and content
            source_user: Username of the person in conversation
            source_telegram_id: Telegram ID for authorization check

        Returns:
            List of extracted Q&A pairs or None
        """
        return await extract_knowledge(
            self.client,
            self.model_haiku,
            conversation,
            source_user,
            source_telegram_id,
        )

    async def save_learned_knowledge(
        self,
        qa_pairs: list[dict],
        source_user: str,
    ) -> int:
        """
        Save extracted knowledge to knowledge base.

        Args:
            qa_pairs: List of Q&A dictionaries
            source_user: Username of the source

        Returns:
            Number of successfully saved entries
        """
        return await save_learned_knowledge(qa_pairs, source_user)

    async def chat_user_with_wallet(
        self,
        message: str,
        user_telegram_id: int,
        user_data: dict[str, Any] | None = None,
        conversation_history: list[dict] | None = None,
        session: Any = None,
    ) -> str:
        """
        Chat for regular users with wallet balance tools.

        Allows ARIA to check user's wallet and recommend PLEX purchases.

        Args:
            message: User's message
            user_telegram_id: User's Telegram ID
            user_data: Optional user context
            conversation_history: Previous messages
            session: Database session

        Returns:
            AI response text
        """
        system_prompt = get_system_prompt(
            UserRole.USER,
            None,
            user_telegram_id,
        )
        context = build_context(UserRole.USER, user_data, None, None)

        return await chat_user_with_wallet(
            self.client,
            self.model_haiku,
            message,
            user_telegram_id,
            system_prompt,
            context,
            user_data,
            conversation_history,
            session,
        )

    async def chat_with_tools(
        self,
        message: str,
        role: UserRole,
        user_data: dict[str, Any] | None = None,
        platform_stats: dict[str, Any] | None = None,
        monitoring_data: str | None = None,
        conversation_history: list[dict] | None = None,
        session: Any = None,
        bot: Any = None,
    ) -> str:
        """
        Chat with tool/function calling support.

        ВАЖНО: Арья выполняет команды от АВТОРИЗОВАННЫХ
        АДМИНОВ!

        Args:
            message: User message
            role: User role
            user_data: User context
            platform_stats: Platform stats
            monitoring_data: Monitoring data
            conversation_history: Previous messages
            session: Database session for broadcast
            bot: Bot instance for sending messages

        Returns:
            AI response
        """
        # Extract username and telegram_id
        username = None
        telegram_id = None
        if user_data:
            username = user_data.get("username") or user_data.get("Имя")
            telegram_id = (
                user_data.get("ID") or user_data.get("telegram_id")
            )
            if isinstance(telegram_id, str):
                try:
                    telegram_id = int(telegram_id)
                except ValueError:
                    telegram_id = None

        system_prompt = get_system_prompt(role, username, telegram_id)
        context = build_context(
            role,
            user_data,
            platform_stats,
            monitoring_data,
        )

        # Try chat with tools first
        result = await chat_with_tools(
            self.client,
            self.model,
            message,
            role,
            system_prompt,
            context,
            user_data,
            conversation_history,
            session,
            bot,
            resolve_admin_id_func=self._resolve_admin_id,
        )

        # If tools not available or error, fall back to regular chat
        if result is None:
            return await self.chat(
                message,
                role,
                user_data,
                platform_stats,
                monitoring_data,
                conversation_history,
            )

        return result

    async def _resolve_admin_id(
        self,
        identifier: str | int,
        session: Any,
    ) -> dict[str, Any] | None:
        """Resolve admin identifier to telegram_id and username."""
        return await resolve_admin_id(identifier, session)


# Singleton instance
_ai_service: AIAssistantService | None = None


def get_ai_service() -> AIAssistantService:
    """Get or create AI service singleton."""
    global _ai_service

    if _ai_service is None:
        from app.config.settings import settings

        _ai_service = AIAssistantService(
            api_key=settings.anthropic_api_key
        )

    return _ai_service
