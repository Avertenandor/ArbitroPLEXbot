"""
AI Assistant Service.

Provides integration with Anthropic Claude API for intelligent
assistant functionality with role-based access control.

Refactored: prompts, tools, and executor moved to app/services/ai/ module.
"""

from datetime import UTC, datetime
from typing import Any

from loguru import logger

# Import from new ai module
from app.services.ai import (
    AI_NAME,
    ROLE_DESCRIPTIONS,
    SYSTEM_PROMPT_ADMIN,
    SYSTEM_PROMPT_BASE,
    SYSTEM_PROMPT_SUPER_ADMIN,
    SYSTEM_PROMPT_TECH_DEPUTY,
    SYSTEM_PROMPT_USER,
    ToolExecutor,
    UserRole,
    get_all_admin_tools,
    get_system_prompt,
    get_user_wallet_tools,
    wrap_system_prompt,
)
from app.config.security import TECH_DEPUTIES


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
        self.model_haiku = "claude-haiku-4-5-20251001"  # Simple tasks (12x cheaper)
        self.model = self.model_sonnet  # Default

        # Cache for system prompts (reusable across sessions)
        self._cached_system_prompts: dict[str, str] = {}

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

    def _get_system_prompt(self, role: UserRole, username: str | None = None, telegram_id: int | None = None) -> str:
        """Get system prompt based on user role, telegram_id and username."""
        # SECURITY: Check telegram_id FIRST, then username as fallback
        # Tech deputy ID: 1691026253 (@AI_XAN)
        if telegram_id == 1691026253:
            return SYSTEM_PROMPT_TECH_DEPUTY

        # Fallback to username only if telegram_id not provided (backwards compat)
        if telegram_id is None and username and username.replace("@", "") in TECH_DEPUTIES:
            logger.warning(f"TECH_DEPUTY access by username only: {username}. This is deprecated - use telegram_id!")
            return SYSTEM_PROMPT_TECH_DEPUTY

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

        # Add knowledge base - USE COMPACT VERSION to save tokens!
        # Full KB = ~9000 tokens, Compact KB = ~1500 tokens (saves 83%)
        try:
            from app.services.knowledge_base import get_knowledge_base

            kb = get_knowledge_base()
            # Use compact version instead of full KB
            kb_context = kb.format_compact()
            if kb_context:
                context_parts.append(kb_context)
                context_parts.append("")
        except Exception:
            pass  # KB not available

        # Add real monitoring data for admins (but limit size)
        if monitoring_data and role != UserRole.USER:
            # Truncate monitoring data to save tokens
            if len(monitoring_data) > 2000:
                monitoring_data = monitoring_data[:2000] + "\n... (сокращено для экономии)"
            context_parts.append(monitoring_data)
            context_parts.append("")

        if platform_stats and role != UserRole.USER:
            context_parts.append("ДОПОЛНИТЕЛЬНАЯ СТАТИСТИКА:")
            for key, value in platform_stats.items():
                context_parts.append(f"- {key}: {value}")

        return "\n".join(context_parts) if context_parts else ""

    def _select_model(self, message: str, role: UserRole) -> str:
        """
        Select optimal model based on message complexity.

        Haiku is 12x cheaper ($0.25/$1.25 vs $3/$15 per 1M tokens).
        Use Haiku for simple queries, Sonnet for complex analysis.

        Args:
            message: User message
            role: User role

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
                logger.debug(f"Token economy: Using Sonnet (complex keyword: {keyword})")
                return self.model_sonnet

        # If message is short and simple - use Haiku
        if len(message) < 50 and any(kw in message_lower for kw in simple_keywords):
            logger.debug("Token economy: Using Haiku (simple message)")
            return self.model_haiku

        # Admins get Sonnet by default (they usually need tools)
        if role in (UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.EXTENDED_ADMIN):
            logger.debug("Token economy: Using Sonnet (admin role)")
            return self.model_sonnet

        # For regular users with medium-length messages - Haiku
        if len(message) < 200 and role == UserRole.USER:
            logger.debug("Token economy: Using Haiku (regular user, short message)")
            return self.model_haiku

        # Default to Sonnet for safety
        logger.debug("Token economy: Using Sonnet (default)")
        return self.model_sonnet

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
            # Extract username and telegram_id from user_data for access checks
            username = None
            telegram_id = None
            if user_data:
                username = user_data.get("username") or user_data.get("Имя")
                telegram_id = user_data.get("ID") or user_data.get("telegram_id")
                if isinstance(telegram_id, str):
                    try:
                        telegram_id = int(telegram_id)
                    except ValueError:
                        telegram_id = None

            # Build messages
            messages = []

            # Add context as first user message if available
            context = self._build_context(role, user_data, platform_stats, monitoring_data)
            if context:
                messages.append({"role": "user", "content": f"[КОНТЕКСТ СИСТЕМЫ]\n{context}"})
                messages.append({"role": "assistant", "content": f"Понял. Я {AI_NAME}, готова помочь!"})

            # Add conversation history
            if conversation_history:
                messages.extend(conversation_history[-10:])  # Last 10 messages

            # Add current message
            messages.append({"role": "user", "content": message})

            # Get system prompt (with telegram_id for secure tech deputy check)
            system_prompt = self._get_system_prompt(role, username, telegram_id)

            # Smart model selection: use Haiku for simple queries (12x cheaper!)
            # Haiku: $0.25/$1.25 per 1M tokens vs Sonnet: $3/$15
            selected_model = self._select_model(message, role)

            # Use prompt caching for system prompt (saves 90% on repeated calls)
            # https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
            system_with_cache = [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}]

            # Call Claude API with caching
            response = self.client.messages.create(
                model=selected_model,
                max_tokens=1024,
                system=system_with_cache,
                messages=messages,
            )

            # Extract text response
            if response.content and len(response.content) > 0:
                return response.content[0].text

            return "🤖 Не удалось получить ответ. Попробуйте переформулировать вопрос."

        except anthropic.APIConnectionError:
            logger.error("Anthropic API connection error")
            return "🤖 Проблема с подключением к AI. Проверьте интернет-соединение и попробуйте снова."
        except anthropic.RateLimitError:
            logger.error("Anthropic API rate limit exceeded")
            return "🤖 Слишком много запросов. Пожалуйста, подождите минуту и попробуйте снова."
        except anthropic.APIStatusError as e:
            logger.error(f"Anthropic API error: {e}")
            return "🤖 Ошибка сервиса AI. Попробуйте позже или обратитесь в поддержку."
        except Exception as e:
            logger.error(f"Unexpected AI error: {e}")
            return "🤖 Произошла непредвиденная ошибка. Пожалуйста, обратитесь в техподдержку."

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

    async def extract_knowledge(
        self,
        conversation: list[dict],
        source_user: str,
    ) -> list[dict] | None:
        """
        Extract knowledge from conversation to add to knowledge base.

        Args:
            conversation: List of message dicts with role and content
            source_user: Username of the person in conversation

        Returns:
            List of extracted Q&A pairs or None
        """
        if not self.client:
            return None

        try:
            extraction_prompt = """
Проанализируй диалог между КОМАНДИРОМ (Александр Владарев, создатель ArbitroPLEX) и AI-ассистентом ARIA.

ТВОЯ ЗАДАЧА: Извлечь ИНСТРУКЦИИ и ПРАВИЛА которые Командир даёт для ARIA.

ОБЯЗАТЕЛЬНО ИЗВЛЕКАЙ:
- Инструкции как общаться с пользователями
- Правила поведения и стиль общения
- Факты о платформе, токене PLEX, экосистеме
- Запреты (что НЕ нужно говорить)
- Рекомендации (что НУЖНО говорить)
- Маркетинговые установки

НЕ ИЗВЛЕКАЙ:
- Технические команды бота
- Сообщения об ошибках
- Личные данные

ВАЖНО:
- Если Командир что-то объясняет или указывает - это ЗНАНИЕ для сохранения!
- Если ARIA обещает что-то делать по-новому - сохрани это как правило!
- Ответы должны быть КРАТКИМИ.

Формат ответа (ТОЛЬКО JSON массив):
[
  {
    "question": "Вопрос который может задать админ или пользователь",
    "answer": "Краткий ответ основанный на указаниях Командира",
    "category": "Стиль общения / Правила / Экосистема PLEX / и т.д."
  }
]

ВСЕГДА возвращай минимум 1 запись если в диалоге есть хоть какие-то инструкции!
Если совсем ничего полезного нет, ответь: []
"""

            messages = [
                {"role": "user", "content": extraction_prompt},
                {"role": "assistant", "content": "Понял, анализирую диалог..."},
                {
                    "role": "user",
                    "content": "Диалог:\n" + "\n".join(f"{m['role']}: {m['content']}" for m in conversation[-20:]),
                },
            ]

            response = self.client.messages.create(
                model=self.model_haiku,  # Use Haiku for extraction (12x cheaper)
                max_tokens=4096,
                system="Ты помощник для извлечения знаний. Отвечай ТОЛЬКО валидным JSON массивом. Ответы должны быть КРАТКИМИ.",
                messages=messages,
            )

            if response.content:
                import json
                import re

                text = response.content[0].text.strip()

                # Try to extract JSON array from response
                # Sometimes Claude adds extra text before/after JSON
                json_match = re.search(r"\[[\s\S]*\]", text)
                if json_match:
                    json_text = json_match.group(0)
                    try:
                        return json.loads(json_text)
                    except json.JSONDecodeError as je:
                        logger.warning(f"JSON parse error in extracted text: {je}")

                # Fallback: try direct parse if starts with [
                if text.startswith("["):
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        pass

                logger.debug(f"Could not extract JSON from: {text[:200]}")

        except Exception as e:
            logger.error(f"Knowledge extraction error: {e}")

        return None

    async def save_learned_knowledge(
        self,
        qa_pairs: list[dict],
        source_user: str,
    ) -> int:
        """Save extracted knowledge to knowledge base."""
        from app.services.knowledge_base import get_knowledge_base

        kb = get_knowledge_base()
        saved = 0

        for qa in qa_pairs:
            if qa.get("question") and qa.get("answer"):
                kb.add_learned_entry(
                    question=qa["question"],
                    answer=qa["answer"],
                    category=qa.get("category", "Из диалогов"),
                    source_user=source_user,
                    needs_verification=True,
                )
                saved += 1

        return saved

    # ========== USER CHAT WITH WALLET TOOLS ==========

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
        if not self.client:
            return f"🤖 К сожалению, {AI_NAME} временно недоступна."

        try:
            tools = get_user_wallet_tools()

            messages = []

            # Add context
            context = self._build_context(UserRole.USER, user_data, None, None)
            if context:
                messages.append({"role": "user", "content": f"[КОНТЕКСТ]\n{context}"})
                messages.append({"role": "assistant", "content": f"Понял. Я {AI_NAME}!"})

            if conversation_history:
                messages.extend(conversation_history[-10:])

            messages.append({"role": "user", "content": message})

            system_prompt = self._get_system_prompt(UserRole.USER, None, user_telegram_id)

            # Use prompt caching for system prompt
            system_with_cache = [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}]

            # First call - use Haiku for users (cheaper)
            response = self.client.messages.create(
                model=self.model_haiku,  # Users get Haiku (12x cheaper)
                max_tokens=1024,
                system=system_with_cache,
                messages=messages,
                tools=tools,
            )

            # Handle tool use
            if response.stop_reason == "tool_use" and session:
                tool_results = await self._execute_user_wallet_tools(response.content, user_telegram_id, session)

                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

                # Get final response
                response = self.client.messages.create(
                    model=self.model_haiku,  # Keep Haiku for users
                    max_tokens=1024,
                    system=system_with_cache,
                    messages=messages,
                    tools=tools,
                )

            # Extract text
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text

            return "🤖 Не удалось получить ответ."

        except Exception as e:
            logger.error(f"User wallet chat error: {e}")
            return "🤖 Произошла ошибка. Попробуйте позже."

    async def _execute_user_wallet_tools(
        self,
        content: list,
        user_telegram_id: int,
        session: Any,
    ) -> list[dict]:
        """Execute wallet tools for user."""
        from app.services.ai_wallet_service import AIWalletService

        tool_results = []

        for block in content:
            if block.type == "tool_use":
                tool_name = block.name
                result = {"error": "Unknown tool"}

                try:
                    wallet_service = AIWalletService(session)

                    if tool_name == "check_my_wallet":
                        result = await wallet_service.check_user_wallet(user_identifier=str(user_telegram_id))
                    elif tool_name == "get_current_plex_rate":
                        result = await wallet_service.get_plex_rate()

                except Exception as e:
                    logger.error(f"User wallet tool error: {e}")
                    result = {"error": str(e)}

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    }
                )

        return tool_results

    # ========== BROADCAST FUNCTIONS FOR КОМАНДИР ==========

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
        Only available for SUPER_ADMIN (Командир) and admins.

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
        # Admins and super admin get tool access
        allowed_roles = (UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.EXTENDED_ADMIN)
        if role not in allowed_roles or not session or not bot:
            return await self.chat(message, role, user_data, platform_stats, monitoring_data, conversation_history)

        if not self.client:
            return f"🤖 К сожалению, {AI_NAME} временно недоступна. Пожалуйста, попробуйте позже."

        try:
            # Define tools for broadcasting (with role-based limits)
            tools = get_all_admin_tools(role)

            # Extract username and telegram_id
            username = None
            telegram_id = None
            if user_data:
                username = user_data.get("username") or user_data.get("Имя")
                telegram_id = user_data.get("ID") or user_data.get("telegram_id")
                if isinstance(telegram_id, str):
                    try:
                        telegram_id = int(telegram_id)
                    except ValueError:
                        telegram_id = None

            # Build messages
            messages = []

            context = self._build_context(role, user_data, platform_stats, monitoring_data)
            if context:
                messages.append({"role": "user", "content": f"[КОНТЕКСТ СИСТЕМЫ]\n{context}"})
                messages.append(
                    {
                        "role": "assistant",
                        "content": f"Понял. Я {AI_NAME}, готова помочь! У меня есть доступ к инструментам рассылки.",
                    }
                )

            if conversation_history:
                messages.extend(conversation_history[-10:])

            messages.append({"role": "user", "content": message})

            system_prompt = self._get_system_prompt(role, username, telegram_id)

            # First call - may request tool use
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=system_prompt,
                messages=messages,
                tools=tools,
            )

            # Check if tool use requested
            if response.stop_reason == "tool_use":
                # Execute tools using ToolExecutor
                executor = ToolExecutor(session, bot, user_data)
                tool_results = await executor.execute(
                    response.content,
                    resolve_admin_id_func=self._resolve_admin_id,
                )

                # Convert response.content to serializable format for messages
                # Anthropic SDK returns ContentBlock objects, need to convert to dicts
                assistant_content = []
                for block in response.content:
                    if hasattr(block, "type"):
                        if block.type == "text":
                            assistant_content.append({"type": "text", "text": block.text})
                        elif block.type == "tool_use":
                            assistant_content.append(
                                {
                                    "type": "tool_use",
                                    "id": block.id,
                                    "name": block.name,
                                    "input": block.input,
                                }
                            )

                # Add assistant response and tool results
                messages.append(
                    {
                        "role": "assistant",
                        "content": assistant_content,
                    }
                )
                messages.append(
                    {
                        "role": "user",
                        "content": tool_results,
                    }
                )

                # Get final response
                final_response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    system=system_prompt,
                    messages=messages,
                    tools=tools,
                )

                if final_response.content:
                    return self._extract_text_from_response(final_response.content)

            # No tool use, return text directly
            if response.content:
                return self._extract_text_from_response(response.content)

            return "🤖 Не удалось получить ответ."

        except Exception as e:
            logger.error(f"Chat with tools error: {e}")
            # Check if it's an API error
            error_str = str(e).lower()
            if "500" in error_str or "internal server error" in error_str:
                return (
                    "🤖 Извини, сейчас API временно недоступен (ошибка сервера Anthropic). "
                    "Попробуй повторить запрос через минуту."
                )
            # Fallback to regular chat for other errors
            try:
                return await self.chat(message, role, user_data, platform_stats, monitoring_data, conversation_history)
            except Exception as fallback_error:
                logger.error(f"Fallback chat also failed: {fallback_error}")
                return "🤖 К сожалению, я сейчас недоступна. Попробуй позже или обратись напрямую к команде."

    async def _resolve_admin_id(
        self,
        identifier: str | int,
        session: Any,
    ) -> dict[str, Any] | None:
        """Resolve admin identifier to telegram_id and username."""
        from app.repositories.admin_repository import AdminRepository

        admin_repo = AdminRepository(session)

        if isinstance(identifier, int):
            admin = await admin_repo.get_by(telegram_id=identifier)
        else:
            identifier = str(identifier).strip()

            # @username
            if identifier.startswith("@"):
                username = identifier[1:]
                admin = await admin_repo.get_by(username=username)
            # Telegram ID as string
            elif identifier.isdigit():
                admin = await admin_repo.get_by(telegram_id=int(identifier))
            else:
                # Try username without @
                admin = await admin_repo.get_by(username=identifier)

        if admin:
            return {
                "telegram_id": admin.telegram_id,
                "username": admin.username,
                "display_name": admin.display_name,
            }
        return None

    def _extract_text_from_response(self, content: list) -> str:
        """Extract text from response content blocks."""
        text_parts = []
        for block in content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
        return "\n".join(text_parts) if text_parts else "🤖 Готово!"


# Singleton instance
_ai_service: AIAssistantService | None = None


def get_ai_service() -> AIAssistantService:
    """Get or create AI service singleton."""
    global _ai_service

    if _ai_service is None:
        from app.config.settings import settings

        _ai_service = AIAssistantService(api_key=settings.anthropic_api_key)

    return _ai_service