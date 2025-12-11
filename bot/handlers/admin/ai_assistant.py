"""
AI Assistant Handler for Admins.

Provides interface for admins to communicate with Claude AI.
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository
from app.services.ai_assistant_service import (
    AI_NAME,
    UserRole,
    get_ai_service,
)
from app.services.monitoring_service import MonitoringService
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import get_admin_keyboard_from_data
from bot.utils.text_utils import escape_markdown


router = Router(name="admin_ai_assistant")


def sanitize_markdown(text: str) -> str:
    """
    Sanitize text to prevent Telegram Markdown parse errors.
    Fixes unclosed formatting and escapes problematic characters.
    """
    if not text:
        return text

    # Count formatting characters
    # Fix unclosed bold markers
    bold_count = text.count("**")
    if bold_count % 2 != 0:
        # Remove the last unpaired **
        last_idx = text.rfind("**")
        text = text[:last_idx] + text[last_idx + 2 :]

    # Fix unclosed single asterisks (italic)
    # First, temporarily replace ** with placeholder
    text = text.replace("**", "\x00BOLD\x00")
    asterisk_count = text.count("*")
    if asterisk_count % 2 != 0:
        # Remove the last unpaired *
        last_idx = text.rfind("*")
        text = text[:last_idx] + text[last_idx + 1 :]
    # Restore bold markers
    text = text.replace("\x00BOLD\x00", "**")

    # Fix unclosed underscores
    # Replace __ with placeholder first
    text = text.replace("__", "\x00UNDER\x00")
    underscore_count = text.count("_")
    if underscore_count % 2 != 0:
        last_idx = text.rfind("_")
        text = text[:last_idx] + text[last_idx + 1 :]
    text = text.replace("\x00UNDER\x00", "__")

    # Fix unclosed backticks
    # Handle code blocks first (```)
    code_block_count = text.count("```")
    if code_block_count % 2 != 0:
        text += "\n```"

    # Handle inline code (single `)
    text = text.replace("```", "\x00CODE\x00")
    backtick_count = text.count("`")
    if backtick_count % 2 != 0:
        last_idx = text.rfind("`")
        text = text[:last_idx] + text[last_idx + 1 :]
    text = text.replace("\x00CODE\x00", "```")

    # Fix unclosed square brackets (links)
    open_brackets = text.count("[")
    close_brackets = text.count("]")
    if open_brackets > close_brackets:
        text += "]" * (open_brackets - close_brackets)

    return text


async def clear_state_keep_session(state: FSMContext) -> None:
    """Clear FSM state but preserve admin session token."""
    state_data = await state.get_data()
    session_token = state_data.get("admin_session_token")
    await state.clear()
    if session_token:
        await state.update_data(admin_session_token=session_token)


class AIAssistantStates(StatesGroup):
    """States for AI assistant interaction."""

    chatting = State()


def ai_assistant_keyboard() -> Any:
    """Create AI assistant keyboard."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📊 Статус системы"),
        KeyboardButton(text="👥 Статистика"),
    )
    builder.row(
        KeyboardButton(text="❓ Помощь по админке"),
        KeyboardButton(text="📚 FAQ"),
    )
    builder.row(KeyboardButton(text="💬 Свободный диалог"))
    builder.row(KeyboardButton(text="◀️ Назад в админку"))
    return builder.as_markup(resize_keyboard=True)


def chat_keyboard() -> Any:
    """Keyboard for chat mode."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🧠 Запомнить это"))
    builder.row(KeyboardButton(text="💬 Написать Дарье"))
    builder.row(KeyboardButton(text="🔚 Завершить диалог"))
    return builder.as_markup(resize_keyboard=True)


async def get_platform_stats(session: AsyncSession) -> dict[str, Any]:
    """Get platform statistics for AI context."""
    try:
        user_repo = UserRepository(session)
        total_users = await user_repo.count()
        verified_users = await user_repo.count_verified_users()

        return {
            "Всего пользователей": total_users,
            "Верифицированных пользователей": verified_users,
        }
    except Exception as e:
        logger.error(f"Error getting platform stats: {e}")
        return {}


async def get_monitoring_data(session: AsyncSession) -> str:
    """Get real-time monitoring data for ARIA."""
    try:
        monitoring = MonitoringService(session)
        dashboard = await monitoring.get_full_dashboard()
        formatted = monitoring.format_dashboard_for_ai(dashboard)

        # Add activity analytics
        activity_report = await monitoring.format_activity_for_aria(24)
        if activity_report and "не активирована" not in activity_report:
            formatted += "\n\n" + activity_report

        # Add AI conversations if available
        ai_conversations = await monitoring.get_ai_conversations_report(24)
        if ai_conversations and "не активировано" not in ai_conversations.lower():
            formatted += "\n\n" + ai_conversations

        logger.debug(f"ARIA context size: {len(formatted)} chars")
        return formatted
    except Exception as e:
        logger.error(f"Error getting monitoring data: {e}")
        return ""


def get_user_role_from_admin(admin: Any) -> UserRole:
    """Convert admin model to UserRole with reliable detection."""
    if admin.is_super_admin:
        return UserRole.SUPER_ADMIN
    elif admin.is_extended_admin:
        return UserRole.EXTENDED_ADMIN
    elif admin.role == "moderator":
        return UserRole.MODERATOR
    else:
        return UserRole.ADMIN


@router.message(StateFilter("*"), F.text == "🤖 AI Помощник")
async def handle_ai_assistant_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show AI assistant menu."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    await clear_state_keep_session(state)

    ai_service = get_ai_service()
    status = "🟢 Онлайн" if ai_service.is_available() else "🔴 Недоступен"
    role = get_user_role_from_admin(admin)
    role_name = {
        UserRole.SUPER_ADMIN: "👑 Владелец",
        UserRole.EXTENDED_ADMIN: "⭐ Расширенный админ",
        UserRole.ADMIN: "👤 Админ",
        UserRole.MODERATOR: "📝 Модератор",
    }.get(role, "👤 Админ")

    await message.answer(
        f"🤖 **{AI_NAME}** — AI Помощник\n\n"
        f"Статус: {status}\n"
        f"Ваш уровень: {role_name}\n\n"
        f"Привет, {escape_markdown(admin.display_name)}! Я {AI_NAME} — твой интеллектуальный помощник.\n\n"
        f"**Что я умею:**\n"
        f"• Отвечать на вопросы о работе платформы\n"
        f"• Помогать с админ-функциями\n"
        f"• Давать советы и рекомендации\n"
        f"• Объяснять сложные вещи простым языком\n\n"
        f"Выбери действие или начни свободный диалог:",
        parse_mode="Markdown",
        reply_markup=ai_assistant_keyboard(),
    )

    logger.info(f"Admin {admin.username} (role={role.value}) opened {AI_NAME}")


@router.message(StateFilter("*"), F.text == "💬 Свободный диалог")
async def start_free_chat(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Start free chat mode with AI."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    await state.set_state(AIAssistantStates.chatting)
    await state.update_data(conversation_history=[])

    await message.answer(
        "💬 **Свободный диалог с AI**\n\n"
        "Теперь можешь писать мне любые вопросы.\n"
        "Я постараюсь помочь!\n\n"
        "Напиши свой вопрос или нажми «Завершить диалог»:",
        parse_mode="Markdown",
        reply_markup=chat_keyboard(),
    )


@router.message(AIAssistantStates.chatting, F.text == "🔚 Завершить диалог")
async def end_chat(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Завершение чата с автоматическим извлечением знаний для ВСЕХ админов."""
    admin = await get_admin_or_deny(message, session, **data)

    # Get conversation history for knowledge extraction
    state_data = await state.get_data()
    history = state_data.get("conversation_history", [])

    logger.info(f"ARIA: Завершение диалога с @{admin.username if admin else 'unknown'}, history_len={len(history)}")

    # Извлечение знаний для ВСЕХ админов (не только super_admin)
    if admin and len(history) >= 2:
        ai_service = get_ai_service()
        username = admin.username or str(admin.telegram_id)

        await message.answer("🧠 Анализирую диалог для извлечения знаний...")
        logger.info(f"ARIA: Начинаю извлечение знаний из {len(history)} сообщений")

        qa_pairs = await ai_service.extract_knowledge(history, username)
        logger.info(f"ARIA: Извлечено qa_pairs={qa_pairs}")

        if qa_pairs:
            saved = await ai_service.save_learned_knowledge(qa_pairs, username)
            logger.info(f"ARIA: Сохранено {saved} записей в базу знаний")
            if saved > 0:
                await message.answer(
                    f"✅ Извлечено {saved} новых записей в базу знаний!\nОни ожидают подтверждения в 📚 База знаний.",
                )
            else:
                await message.answer("ℹ️ Не удалось извлечь новые знания из этого диалога.")
        else:
            await message.answer("ℹ️ В этом диалоге не найдено новых знаний для сохранения.")
    elif admin and len(history) < 2:
        logger.info(f"ARIA: Слишком короткий диалог ({len(history)} сообщений), пропускаю извлечение")

    await clear_state_keep_session(state)
    await message.answer(
        "✅ Диалог завершён.\n\nБыло приятно пообщаться! Возвращайся, если будут вопросы.",
        reply_markup=ai_assistant_keyboard(),
    )


@router.message(AIAssistantStates.chatting, F.text == "🧠 Запомнить это")
async def manual_save_knowledge(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Ручное извлечение и сохранение знаний из текущего диалога."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    state_data = await state.get_data()
    history = state_data.get("conversation_history", [])

    logger.info(f"ARIA: Ручное сохранение знаний от @{admin.username}, history_len={len(history)}")

    if len(history) < 2:
        await message.answer(
            "ℹ️ Диалог слишком короткий для извлечения знаний.\nПродолжи общение и попробуй снова!",
            reply_markup=chat_keyboard(),
        )
        return

    ai_service = get_ai_service()
    username = admin.username or str(admin.telegram_id)

    await message.answer("🧠 Анализирую диалог и извлекаю знания...")

    qa_pairs = await ai_service.extract_knowledge(history, username)
    logger.info(f"ARIA: Ручное извлечение - qa_pairs={qa_pairs}")

    if qa_pairs:
        saved = await ai_service.save_learned_knowledge(qa_pairs, username)
        logger.info(f"ARIA: Ручное сохранение - saved={saved}")
        if saved > 0:
            await message.answer(
                f"✅ Отлично! Извлечено и сохранено {saved} записей!\n\n"
                "Они добавлены в базу знаний и ожидают подтверждения.\n"
                "Продолжай диалог! 💬",
                reply_markup=chat_keyboard(),
            )
        else:
            await message.answer(
                "ℹ️ Не удалось сохранить извлечённые знания.\nПопробуй сформулировать информацию более чётко.",
                reply_markup=chat_keyboard(),
            )
    else:
        await message.answer(
            "ℹ️ Не удалось извлечь полезные знания из диалога.\n\n"
            "💡 Попробуй:\n"
            "• Объяснить что-то конкретное о системе\n"
            "• Дать чёткую инструкцию\n"
            "• Рассказать о важном правиле",
            reply_markup=chat_keyboard(),
        )


@router.message(AIAssistantStates.chatting, F.text == "💬 Написать Дарье")
async def switch_to_darya_chat(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    redis_client=None,
    **data: Any,
) -> None:
    """Switch from ARIA chat to Darya (developer) chat without leaving the dialog."""
    from bot.handlers.admin.dev_chat import DevChatStates, get_dev_chat_keyboard

    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    # Save current ARIA state so we can return
    state_data = await state.get_data()
    state_data["return_to_aria"] = True
    await state.update_data(return_to_aria=True)

    # Switch to Darya chat state
    await state.set_state(DevChatStates.writing_message)

    await message.answer(
        "💬 **Переключаюсь на Дарью (разработчика)**\n\n"
        "Привет! Я Дарья — ИИ-разработчик бота (Copilot/Claude).\n\n"
        "Напиши мне:\n"
        "• Что неудобно в боте?\n"
        "• Какие функции добавить?\n"
        "• Какие баги исправить?\n"
        "• Любые идеи и предложения!\n\n"
        "✍️ **Просто напиши сообщение ниже:**\n\n"
        "_После отправки вернёшься к ARIA._",
        parse_mode="Markdown",
        reply_markup=get_dev_chat_keyboard(),
    )
    logger.info(f"Admin @{admin.username} switched from ARIA to Darya chat")


@router.message(AIAssistantStates.chatting)
async def handle_chat_message(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle chat message to AI."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    user_message = message.text or ""
    if not user_message.strip():
        return

    # ========== CHECK FOR ACTIVE INTERVIEW ==========
    from app.services.ai_interview_service import get_interview_service

    interview_service = get_interview_service(message.bot)
    if interview_service and interview_service.has_active_interview(admin.telegram_id):
        # This admin is being interviewed - process the answer
        result = await interview_service.process_answer(
            target_admin_id=admin.telegram_id,
            answer_text=user_message,
        )

        if result.get("completed"):
            # Interview completed - save to knowledge base
            ai_service = get_ai_service()
            answers = result.get("answers", [])
            topic = result.get("topic", "")

            if answers:
                # Convert to QA pairs for knowledge base
                qa_pairs = []
                for qa in answers:
                    qa_pairs.append(
                        {
                            "question": qa["question"],
                            "answer": qa["answer"],
                            "category": topic,
                        }
                    )

                # Save to knowledge base
                saved = await ai_service.save_learned_knowledge(qa_pairs, result.get("target", "interview"))

                logger.info(f"Interview completed: saved {saved} entries from @{result.get('target')}")

        # Don't process as regular message - interview handler took care of it
        return

    # ========== SECURITY CHECKS ==========
    from app.services.admin_security_service import VERIFIED_ADMIN_IDS
    from app.services.aria_security_defense import (
        SECURITY_RESPONSE_BLOCKED,
        SECURITY_RESPONSE_FORWARDED,
        check_forwarded_message,
        create_secure_context,
        get_security_guard,
        sanitize_user_input,
    )

    # Check for forwarded messages
    forward_check = check_forwarded_message(message)
    if forward_check["is_forwarded"]:
        logger.warning(
            f"SECURITY: Forwarded message from admin {admin.telegram_id} (@{admin.username}). Original: {forward_check}"
        )
        await message.answer(
            SECURITY_RESPONSE_FORWARDED,
            parse_mode="Markdown",
            reply_markup=chat_keyboard(),
        )
        return

    # Check for security threats in message
    security_guard = get_security_guard()
    security_check = security_guard.check_message(
        text=user_message,
        telegram_id=admin.telegram_id,
        username=admin.username,
        is_admin=True,
    )

    if not security_check["allow"]:
        logger.error(
            f"🚨 SECURITY BLOCK: Admin {admin.telegram_id} message blocked. Reason: {security_check['block_reason']}"
        )
        await message.answer(
            SECURITY_RESPONSE_BLOCKED,
            parse_mode="Markdown",
            reply_markup=chat_keyboard(),
        )
        return

    # Add warnings to context if any
    security_warnings = security_check.get("warnings", [])

    # Verify admin identity
    is_verified = admin.telegram_id in VERIFIED_ADMIN_IDS

    # Sanitize user input
    sanitized_message = sanitize_user_input(user_message)

    # Create secure context
    admin_role = VERIFIED_ADMIN_IDS.get(admin.telegram_id, {}).get("role", admin.role)
    secure_context = create_secure_context(
        telegram_id=admin.telegram_id,
        username=admin.username,
        is_admin=True,
        is_verified_admin=is_verified,
        admin_role=admin_role,
    )
    # ========== END SECURITY CHECKS ==========

    # Show typing indicator
    await message.answer("🤔 Думаю...")

    # Get conversation history
    state_data = await state.get_data()
    history = state_data.get("conversation_history", [])

    # Get AI service and role
    ai_service = get_ai_service()
    role = get_user_role_from_admin(admin)

    # Get platform stats for context
    platform_stats = await get_platform_stats(session)

    # Get real-time monitoring data
    monitoring_data = await get_monitoring_data(session)

    # Admin context with security info
    admin_data = {
        "Имя": admin.display_name,
        "Роль": admin.role_display,
        "ID": admin.telegram_id,
        "username": getattr(admin, "username", None),
        "is_verified": is_verified,
        "security_context": secure_context,
        "security_warnings": security_warnings,
    }

    # Prepend security context to sanitized message
    message_with_context = secure_context + sanitized_message

    # Use chat_with_tools for super admin (Командир) to enable broadcasting
    if role == UserRole.SUPER_ADMIN:
        response = await ai_service.chat_with_tools(
            message=message_with_context,
            role=role,
            user_data=admin_data,
            platform_stats=platform_stats,
            monitoring_data=monitoring_data,
            conversation_history=history,
            session=session,
            bot=message.bot,
        )
    elif role in (UserRole.ADMIN, UserRole.EXTENDED_ADMIN):
        # Admins also get tool access (with limits)
        response = await ai_service.chat_with_tools(
            message=message_with_context,
            role=role,
            user_data=admin_data,
            platform_stats=platform_stats,
            monitoring_data=monitoring_data,
            conversation_history=history,
            session=session,
            bot=message.bot,
        )
    else:
        # Regular chat for users (should not happen in admin handler)
        response = await ai_service.chat(
            message=message_with_context,
            role=role,
            user_data=admin_data,
            platform_stats=platform_stats,
            monitoring_data=monitoring_data,
            conversation_history=history,
        )

    # Update history (save original message without security context)
    history.append({"role": "user", "content": sanitized_message})
    history.append({"role": "assistant", "content": response})

    # Keep only last 20 messages
    if len(history) > 20:
        history = history[-20:]

    await state.update_data(conversation_history=history)

    # Sanitize markdown to prevent parse errors
    safe_response = sanitize_markdown(response)

    await message.answer(
        safe_response,
        parse_mode="Markdown",
        reply_markup=chat_keyboard(),
    )

    # Log AI conversation in separate session (non-blocking)
    # Using separate session to avoid transaction conflicts
    try:
        from app.config.database import async_session_maker
        from app.services.user_activity_service import UserActivityService

        async with async_session_maker() as log_session:
            activity_service = UserActivityService(log_session)
            await activity_service.log_ai_conversation_safe(
                telegram_id=admin.telegram_id,
                admin_name=admin.display_name or admin.username or "Unknown",
                question=sanitized_message,  # Log sanitized version
                answer=response,
            )
            await log_session.commit()
            logger.debug(f"AI conversation logged for {admin.username}")
    except Exception as log_error:
        logger.warning(f"AI conversation logging failed: {log_error}")

    logger.info(f"AI chat with admin {admin.username}: {user_message[:50]}...")


@router.message(StateFilter("*"), F.text == "📊 Статус системы")
async def show_system_status(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show system status via AI."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    ai_service = get_ai_service()
    role = get_user_role_from_admin(admin)
    monitoring_data = await get_monitoring_data(session)

    response = await ai_service.chat(
        message="Дай краткий отчёт о текущем статусе системы на основе мониторинга.",
        role=role,
        monitoring_data=monitoring_data,
    )

    safe_response = sanitize_markdown(response)
    await message.answer(
        f"📊 **Статус системы**\n\n{safe_response}",
        parse_mode="Markdown",
        reply_markup=ai_assistant_keyboard(),
    )


@router.message(StateFilter("*"), F.text == "👥 Статистика")
async def show_stats(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show platform statistics."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    # Get comprehensive stats via monitoring service
    monitoring = MonitoringService(session)
    dashboard = await monitoring.get_full_dashboard()

    users = dashboard.get("users", {})
    fin = dashboard.get("financial", {})
    admin_stats = dashboard.get("admin", {})

    text = "👥 **Статистика платформы**\n\n"
    text += "**Пользователи:**\n"
    text += f"• Всего: **{users.get('total_users', 0)}**\n"
    text += f"• Активных (24ч): **{users.get('active_24h', 0)}**\n"
    text += f"• Активных (7д): **{users.get('active_7d', 0)}**\n"
    text += f"• Новых за час: **{users.get('new_last_hour', 0)}**\n"
    text += f"• Новых сегодня: **{users.get('new_today', 0)}**\n"
    text += f"• Верифицированных: **{users.get('verified_users', 0)}**\n\n"
    text += "**Финансы:**\n"
    text += f"• Депозитов: **${fin.get('total_active_deposits', 0):,.2f}**\n"
    text += f"• Ожидают вывода: **{fin.get('pending_withdrawals_count', 0)}** "
    text += f"(${fin.get('pending_withdrawals_amount', 0):,.2f})\n\n"
    text += "**Администраторы:**\n"
    text += f"• Всего: **{admin_stats.get('total_admins', 0)}**\n"
    text += f"• Активных (24ч): **{admin_stats.get('active_admins_last_hours', 0)}**\n"
    text += f"• Действий (24ч): **{admin_stats.get('total_actions', 0)}**\n"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=ai_assistant_keyboard(),
    )


@router.message(StateFilter("*"), F.text == "❓ Помощь по админке")
async def show_admin_help(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show admin panel help."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    ai_service = get_ai_service()
    role = get_user_role_from_admin(admin)

    response = await ai_service.chat(
        message="Объясни основные функции админ-панели и где что найти.",
        role=role,
    )

    safe_response = sanitize_markdown(response)
    await message.answer(
        f"❓ **Справка по админ-панели**\n\n{safe_response}",
        parse_mode="Markdown",
        reply_markup=ai_assistant_keyboard(),
    )


@router.message(StateFilter("*"), F.text == "📚 FAQ")
async def show_faq(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show FAQ."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    ai_service = get_ai_service()
    role = get_user_role_from_admin(admin)

    response = await ai_service.chat(
        message="Дай топ-5 частых вопросов от пользователей и краткие ответы.",
        role=role,
    )

    safe_response = sanitize_markdown(response)
    await message.answer(
        f"📚 **Частые вопросы**\n\n{safe_response}",
        parse_mode="Markdown",
        reply_markup=ai_assistant_keyboard(),
    )


@router.message(StateFilter("*"), F.text == "◀️ Назад в админку")
async def back_to_admin(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Return to admin panel."""
    await clear_state_keep_session(state)
    await message.answer(
        "👑 Возвращаюсь в админ-панель...",
        reply_markup=get_admin_keyboard_from_data(data),
    )
