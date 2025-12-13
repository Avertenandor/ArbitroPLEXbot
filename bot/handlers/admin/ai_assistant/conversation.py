"""
AI Assistant conversation handlers.

Contains handlers for AI chat interactions.
"""

from typing import Any

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_assistant_service import UserRole, get_ai_service
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.utils.text_utils import sanitize_markdown

from .utils import (
    ai_assistant_keyboard,
    chat_keyboard,
    clear_state_keep_session,
    get_monitoring_data,
    get_platform_stats,
    get_user_role_from_admin,
    _get_admin_capabilities_text,
    _is_capabilities_question,
    AIAssistantStates,
)

router = Router(name="admin_ai_conversation")


@router.message(
    AIAssistantStates.chatting,
    lambda m: m.text == "🔚 Завершить диалог",
)
async def end_chat(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Завершение чата с извлечением знаний.

    Для ВСЕХ админов из ARYA_TEACHERS.
    """
    admin = await get_admin_or_deny(message, session, **data)

    # Get conversation history for knowledge extraction
    state_data = await state.get_data()
    history = state_data.get("conversation_history", [])

    logger.info(
        f"ARIA: Завершение диалога с "
        f"@{admin.username if admin else 'unknown'}, "
        f"history_len={len(history)}",
    )
    # Извлечение знаний для ВСЕХ админов из ARYA_TEACHERS
    if admin and len(history) >= 2:
        ai_service = get_ai_service()
        username = admin.username or str(admin.telegram_id)

        await message.answer(
            "🧠 Анализирую диалог для извлечения знаний...",
        )
        logger.info(
            f"ARIA: Начинаю извлечение знаний из {len(history)} "
            f"сообщений от admin_id={admin.telegram_id}",
        )
        qa_pairs = await ai_service.extract_knowledge(
            history,
            username,
            source_telegram_id=admin.telegram_id,
        )
        logger.info(f"ARIA: Извлечено qa_pairs={qa_pairs}")

        if qa_pairs:
            saved = await ai_service.save_learned_knowledge(
                qa_pairs,
                username,
            )
            logger.info(
                f"ARIA: Сохранено {saved} записей в базу знаний",
            )
            if saved > 0:
                await message.answer(
                    f"✅ Извлечено {saved} новых записей "
                    "в базу знаний!\n"
                    "Они ожидают подтверждения в "
                    "📚 База знаний.",
                )
            else:
                await message.answer(
                    "ℹ️ Не удалось извлечь новые знания "
                    "из этого диалога.",
                )
        else:
            await message.answer(
                "ℹ️ В этом диалоге не найдено новых знаний "
                "для сохранения.",
            )
    elif admin and len(history) < 2:
        logger.info(
            f"ARIA: Слишком короткий диалог ({len(history)} "
            "сообщений), пропускаю извлечение",
        )

    await clear_state_keep_session(state)
    await message.answer(
        "✅ Диалог завершён.\n\n"
        "Было приятно пообщаться! "
        "Возвращайся, если будут вопросы.",
        reply_markup=ai_assistant_keyboard(),
    )


@router.message(
    AIAssistantStates.chatting,
    lambda m: m.text == "🧠 Запомнить это",
)
async def manual_save_knowledge(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Ручное извлечение и сохранение знаний."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    state_data = await state.get_data()
    history = state_data.get("conversation_history", [])

    logger.info(
        f"ARIA: Ручное сохранение знаний от @{admin.username}, "
        f"history_len={len(history)}",
    )
    if len(history) < 2:
        await message.answer(
            "ℹ️ Диалог слишком короткий для "
            "извлечения знаний.\n"
            "Продолжи общение и попробуй снова!",
            reply_markup=chat_keyboard(),
        )
        return

    ai_service = get_ai_service()
    username = admin.username or str(admin.telegram_id)
    await message.answer(
        "🧠 Анализирую диалог и извлекаю знания...",
    )
    qa_pairs = await ai_service.extract_knowledge(
        history,
        username,
        source_telegram_id=admin.telegram_id,
    )
    logger.info(
        f"ARIA: Ручное извлечение от admin_id={admin.telegram_id}"
        f" - qa_pairs={qa_pairs}",
    )

    if qa_pairs:
        saved = await ai_service.save_learned_knowledge(
            qa_pairs,
            username,
        )
        logger.info(f"ARIA: Ручное сохранение - saved={saved}")
        if saved > 0:
            await message.answer(
                f"✅ Отлично! Извлечено и сохранено {saved} "
                "записей!\n\n"
                "Они добавлены в базу знаний и ожидают "
                "подтверждения.\n"
                "Продолжай диалог! 💬",
                reply_markup=chat_keyboard(),
            )
        else:
            await message.answer(
                "ℹ️ Не удалось сохранить "
                "извлечённые знания.\n"
                "Попробуй сформулировать информацию "
                "более чётко.",
                reply_markup=chat_keyboard(),
            )
    else:
        await message.answer(
            "ℹ️ Не удалось извлечь полезные знания "
            "из диалога.\n\n"
            "💡 Попробуй:\n"
            "• Объяснить что-то конкретное о системе\n"
            "• Дать чёткую инструкцию\n"
            "• Рассказать о важном правиле",
            reply_markup=chat_keyboard(),
        )


@router.message(
    AIAssistantStates.chatting,
    lambda m: m.text == "💬 Написать Дарье",
)
async def switch_to_darya_chat(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    redis_client=None,
    **data: Any,
) -> None:
    """
    Switch from ARIA to Darya (developer) chat.

    Without leaving the dialog.
    """
    from bot.handlers.admin.dev_chat import (
        DevChatStates,
        get_dev_chat_keyboard,
    )

    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    state_data = await state.get_data()
    state_data["return_to_aria"] = True
    await state.update_data(return_to_aria=True)
    await state.set_state(DevChatStates.writing_message)
    await message.answer(
        "💬 **Переключаюсь на Дарью (разработчика)**\n\n"
        "Привет! Я Дарья — ИИ-разработчик бота "
        "(Copilot/Claude).\n\n"
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
    logger.info(
        f"Admin @{admin.username} switched from ARIA "
        "to Darya chat",
    )


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
    # Если админ спрашивает про мои полномочия —
    # отвечаем статическим текстом даже при
    # недоступности внешнего AI.
    if _is_capabilities_question(user_message):
        role = get_user_role_from_admin(admin)
        capabilities_text = _get_admin_capabilities_text(role)
        await message.answer(
            capabilities_text,
            parse_mode="Markdown",
            reply_markup=chat_keyboard(),
        )
        return
    # ========== CHECK FOR ACTIVE INTERVIEW ==========
    from app.services.ai_interview_service import (
        get_interview_service,
    )

    interview_service = get_interview_service(message.bot)
    if interview_service and interview_service.has_active_interview(
        admin.telegram_id,
    ):
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
                saved = await ai_service.save_learned_knowledge(
                    qa_pairs,
                    result.get("target", "interview"),
                )

                logger.info(
                    f"Interview completed: saved {saved} entries "
                    f"from @{result.get('target')}",
                )
        # Don't process as regular message
        return
    # ========== SECURITY CHECKS ==========
    from app.config.admin_config import VERIFIED_ADMIN_IDS
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
            f"SECURITY: Forwarded message from admin "
            f"{admin.telegram_id} (@{admin.username}). "
            f"Original: {forward_check}",
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
            f"🚨 SECURITY BLOCK: Admin {admin.telegram_id} "
            f"message blocked. "
            f"Reason: {security_check['block_reason']}",
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
    admin_role = VERIFIED_ADMIN_IDS.get(
        admin.telegram_id,
        {},
    ).get("role", admin.role)
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
    # Use chat_with_tools for super admin (Командир)
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
    try:
        from app.config.database import async_session_maker
        from app.services.user_activity_service import (
            UserActivityService,
        )

        async with async_session_maker() as log_session:
            activity_service = UserActivityService(log_session)
            await activity_service.log_ai_conversation_safe(
                telegram_id=admin.telegram_id,
                admin_name=(
                    admin.display_name
                    or admin.username
                    or "Unknown"
                ),
                question=sanitized_message,
                answer=response,
            )
            await log_session.commit()
            logger.debug(
                f"AI conversation logged for {admin.username}",
            )
    except Exception as log_error:
        logger.warning(
            f"AI conversation logging failed: {log_error}",
        )
    logger.info(
        f"AI chat with admin {admin.username}: "
        f"{user_message[:50]}...",
    )
