"""
Tool Processor for AI Assistant.

Handles tool execution for admin and user commands.
"""

from typing import Any, Callable

from loguru import logger

from app.config.operational_constants import (
    AI_MAX_TOKENS_MEDIUM,
    AI_MAX_TOKENS_SHORT,
)
from app.config.security import can_command_arya
from app.services.ai import (
    AI_NAME,
    ToolExecutor,
    UserRole,
    extract_text_from_response,
    get_all_admin_tools,
    get_user_wallet_tools,
    wrap_system_prompt,
)


async def execute_user_wallet_tools(
    content: list,
    user_telegram_id: int,
    session: Any,
) -> list[dict]:
    """
    Execute wallet tools for user.

    Args:
        content: Response content blocks
        user_telegram_id: User's Telegram ID
        session: Database session

    Returns:
        List of tool result dictionaries
    """
    from app.services.ai_wallet_service import AIWalletService

    tool_results = []

    for block in content:
        if block.type == "tool_use":
            tool_name = block.name
            result = {"error": "Unknown tool"}

            try:
                wallet_service = AIWalletService(session)

                if tool_name == "check_my_wallet":
                    result = await wallet_service.check_user_wallet(
                        user_identifier=str(user_telegram_id)
                    )
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


async def chat_user_with_wallet(
    client: Any,
    model_haiku: str,
    message: str,
    user_telegram_id: int,
    system_prompt: str,
    context: str,
    user_data: dict[str, Any] | None = None,
    conversation_history: list[dict] | None = None,
    session: Any = None,
) -> str:
    """
    Chat for regular users with wallet balance tools.

    Allows ARIA to check user's wallet and recommend PLEX purchases.

    Args:
        client: Anthropic client
        model_haiku: Haiku model name
        message: User's message
        user_telegram_id: User's Telegram ID
        system_prompt: System prompt
        context: Context string
        user_data: Optional user context
        conversation_history: Previous messages
        session: Database session

    Returns:
        AI response text
    """
    if not client:
        return f"🤖 К сожалению, {AI_NAME} временно недоступна."

    try:
        tools = get_user_wallet_tools()

        messages = []

        # Add context
        if context:
            messages.append({"role": "user", "content": f"[КОНТЕКСТ]\n{context}"})
            messages.append(
                {
                    "role": "assistant",
                    "content": f"Понял. Я {AI_NAME}!",
                }
            )

        if conversation_history:
            messages.extend(conversation_history[-10:])

        messages.append({"role": "user", "content": message})

        # Use prompt caching for system prompt
        system_with_cache = [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        # First call - use Haiku for users (cheaper)
        response = client.messages.create(
            model=model_haiku,  # Users get Haiku (12x cheaper)
            max_tokens=AI_MAX_TOKENS_SHORT,
            system=system_with_cache,
            messages=messages,
            tools=tools,
        )

        # Handle tool use
        if response.stop_reason == "tool_use":
            if not session:
                logger.error(
                    f"Tool use requested but session is None for user "
                    f"{user_telegram_id}"
                )
                return (
                    "🤖 Ошибка: сессия базы данных недоступна. "
                    "Попробуйте позже."
                )

            tool_results = await execute_user_wallet_tools(
                response.content,
                user_telegram_id,
                session,
            )

            # Serialize response.content to JSON-compatible format
            assistant_content = []
            for block in response.content:
                if hasattr(block, "type"):
                    if block.type == "text":
                        assistant_content.append(
                            {"type": "text", "text": block.text}
                        )
                    elif block.type == "tool_use":
                        assistant_content.append(
                            {
                                "type": "tool_use",
                                "id": block.id,
                                "name": block.name,
                                "input": block.input,
                            }
                        )
            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results})

            # Get final response (no tools - final answer should be text only)
            response = client.messages.create(
                model=model_haiku,  # Keep Haiku for users
                max_tokens=AI_MAX_TOKENS_SHORT,
                system=system_with_cache,
                messages=messages,
            )

        # Extract text
        for block in response.content:
            if hasattr(block, "text"):
                return block.text

        return "🤖 Не удалось получить ответ."

    except Exception as e:
        logger.error(f"User wallet chat error: {e}")
        return "🤖 Произошла ошибка. Попробуйте позже."


async def chat_with_tools(
    client: Any,
    model: str,
    message: str,
    role: UserRole,
    system_prompt: str,
    context: str,
    user_data: dict[str, Any] | None = None,
    conversation_history: list[dict] | None = None,
    session: Any = None,
    bot: Any = None,
    resolve_admin_id_func: Callable | None = None,
) -> str:
    """
    Chat with tool/function calling support.

    ВАЖНО: Арья выполняет команды от АВТОРИЗОВАННЫХ
    АДМИНОВ! Проверка через can_command_arya() - список
    в security.py.

    Арья сама является администратором (extended_admin)
    и выполняет команды от имени системы, НЕ от имени
    собеседника.

    Args:
        client: Anthropic client
        model: Model name to use
        message: User message
        role: User role
        system_prompt: System prompt
        context: Context string
        user_data: User context
        conversation_history: Previous messages
        session: Database session for broadcast
        bot: Bot instance for sending messages
        resolve_admin_id_func: Function to resolve admin identifiers

    Returns:
        AI response
    """
    # Извлекаем telegram_id собеседника для проверки прав
    caller_telegram_id: int | None = None
    if user_data:
        caller_telegram_id = (
            user_data.get("ID") or user_data.get("telegram_id")
        )
        if isinstance(caller_telegram_id, str):
            try:
                caller_telegram_id = int(caller_telegram_id)
            except ValueError:
                caller_telegram_id = None

    # КРИТИЧЕСКИ ВАЖНО: Проверяем может ли собеседник
    # командовать Арьей. Теперь любому действующему
    # админу (есть запись в БД и он не заблокирован)
    # разрешено отдавать команды, а уже внутри
    # инструментов ограничения накладываются по его
    # реальной роли и проверкам внутри инструментов.
    caller_can_command = False

    if session and caller_telegram_id:
        # 1) Сначала сохраняем старый whitelist
        # для обратной совместимости
        if can_command_arya(caller_telegram_id):
            caller_can_command = True
        else:
            # 2) Если не в ARYA_COMMAND_GIVERS, проверяем,
            # что это реальный админ в БД
            try:
                from app.repositories.admin_repository import (
                    AdminRepository,
                )

                admin_repo = AdminRepository(session)
                admin_obj = await admin_repo.get_by_telegram_id(
                    caller_telegram_id
                )

                if admin_obj and not admin_obj.is_blocked:
                    caller_can_command = True
                else:
                    logger.warning(
                        "ARYA: caller is not allowed to command "
                        "(not admin or blocked)",
                        extra={"caller_telegram_id": caller_telegram_id},
                    )
            except Exception as e:
                logger.error(
                    f"ARYA: failed to verify admin rights for caller "
                    f"{caller_telegram_id}: {e}"
                )

    # Если нет сессии/бота или собеседник не может
    # командовать - return None to fall back to regular chat
    if not session or not bot or not caller_can_command:
        return None

    # Арья выполняет команды как SUPER_ADMIN для любого
    # действующего админа. (Требование: все админы могут
    # командовать Арьей «как супер админ».)
    arya_role = UserRole.SUPER_ADMIN

    if not client:
        return (
            f"🤖 К сожалению, {AI_NAME} временно недоступна. "
            "Пожалуйста, попробуйте позже."
        )

    try:
        # ВАЖНО: Инструменты определяются по роли АРЬИ,
        # не собеседника! Арья - extended_admin
        # (или super_admin для Командира)
        tools = get_all_admin_tools(arya_role)
        logger.info(
            f"ARYA: executing commands from "
            f"telegram_id={caller_telegram_id}, arya_role={arya_role.value}"
        )

        # Build messages
        messages = []

        if context:
            messages.append(
                {"role": "user", "content": f"[КОНТЕКСТ СИСТЕМЫ]\n{context}"}
            )
            messages.append(
                {
                    "role": "assistant",
                    "content": (
                        f"Понял. Я {AI_NAME}, готова помочь! "
                        "У меня есть доступ к инструментам "
                        "рассылки."
                    ),
                }
            )

        if conversation_history:
            messages.extend(conversation_history[-10:])

        messages.append({"role": "user", "content": message})

        # First call - may request tool use
        # Use prompt caching (saves 90% on repeated calls)
        system_with_cache = wrap_system_prompt(system_prompt)

        response = client.messages.create(
            model=model,
            max_tokens=AI_MAX_TOKENS_MEDIUM,
            system=system_with_cache,
            messages=messages,
            tools=tools,
        )

        # Check if tool use requested
        if response.stop_reason == "tool_use":
            # Execute tools using ToolExecutor
            # ВАЖНО: передаём caller_telegram_id для логирования
            # и rate limiting
            executor = ToolExecutor(
                session,
                bot,
                user_data,
                caller_telegram_id=caller_telegram_id,
            )
            tool_results = await executor.execute(
                response.content,
                resolve_admin_id_func=resolve_admin_id_func,
            )

            # Convert response.content to serializable format for messages
            # Anthropic SDK returns ContentBlock objects,
            # need to convert to dicts
            assistant_content = []
            for block in response.content:
                if hasattr(block, "type"):
                    if block.type == "text":
                        assistant_content.append(
                            {"type": "text", "text": block.text}
                        )
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

            # Get final response (no tools - final answer should be text only)
            final_response = client.messages.create(
                model=model,
                max_tokens=AI_MAX_TOKENS_MEDIUM,
                system=system_with_cache,
                messages=messages,
            )

            if final_response.content:
                return extract_text_from_response(final_response.content)

        # No tool use, return text directly
        if response.content:
            return extract_text_from_response(response.content)

        return "🤖 Не удалось получить ответ."

    except Exception as e:
        logger.error(f"Chat with tools error: {e}")
        # Check if it's an API error
        error_str = str(e).lower()
        if "500" in error_str or "internal server error" in error_str:
            return (
                "🤖 Извини, сейчас API временно недоступен "
                "(ошибка сервера Anthropic). "
                "Попробуй повторить запрос через минуту."
            )
        # Return None to fall back to regular chat
        return None


async def resolve_admin_id(
    identifier: str | int,
    session: Any,
) -> dict[str, Any] | None:
    """
    Resolve admin identifier to telegram_id and username.

    Args:
        identifier: Admin identifier (username or telegram_id)
        session: Database session

    Returns:
        Admin data dict or None
    """
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
