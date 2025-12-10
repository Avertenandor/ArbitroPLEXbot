"""
AI Assistant Handler for Users.

Provides interface for regular users to communicate with Claude AI
with restricted access to sensitive information.
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

from app.services.ai_assistant_service import AI_NAME, UserRole, get_ai_service
from bot.utils.text_utils import escape_markdown, safe_answer, sanitize_markdown


router = Router(name="user_ai_assistant")


class UserAIStates(StatesGroup):
    """States for user AI chat."""

    chatting = State()


def user_ai_keyboard() -> Any:
    """Create user AI assistant keyboard."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="❓ Как работает платформа?"),
        KeyboardButton(text="💰 Про депозиты"),
    )
    builder.row(
        KeyboardButton(text="💸 Про выводы"),
        KeyboardButton(text="👥 Про рефералов"),
    )
    builder.row(KeyboardButton(text="💬 Задать вопрос"))
    builder.row(KeyboardButton(text="◀️ Главное меню"))
    return builder.as_markup(resize_keyboard=True)


def user_chat_keyboard() -> Any:
    """Keyboard for user chat mode."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🔚 Закончить"))
    return builder.as_markup(resize_keyboard=True)


@router.message(StateFilter("*"), F.text == "🤖 Помощник")
async def user_ai_menu(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show AI assistant menu for users."""
    await state.clear()

    ai_service = get_ai_service()
    status = "🟢 Онлайн" if ai_service.is_available() else "🔴 Недоступен"
    user_name = escape_markdown(message.from_user.first_name or "друг")

    await message.answer(
        f"🤖 **{AI_NAME}** — AI Помощник\n\n"
        f"Статус: {status}\n\n"
        f"Привет, {user_name}! Я {AI_NAME} — интеллектуальный помощник "
        f"платформы ArbitroPLEX.\n\n"
        f"Могу рассказать о:\n"
        f"• Как работает платформа\n"
        f"• Депозиты и доходность\n"
        f"• Выводы средств\n"
        f"• Реферальная программа\n\n"
        f"Выбери тему или задай свой вопрос:",
        parse_mode="Markdown",
        reply_markup=user_ai_keyboard(),
    )


@router.message(StateFilter("*"), F.text == "💬 Задать вопрос")
async def start_user_chat(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Start chat mode for user."""
    await state.set_state(UserAIStates.chatting)
    await state.update_data(conversation_history=[])

    await message.answer(
        "💬 **Свободный диалог**\n\n"
        "Напиши свой вопрос, и я постараюсь помочь!\n\n"
        "Нажми «Закончить» чтобы вернуться в меню.",
        parse_mode="Markdown",
        reply_markup=user_chat_keyboard(),
    )


@router.message(UserAIStates.chatting, F.text == "🔚 Закончить")
async def end_user_chat(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """End user chat."""
    await state.clear()
    await message.answer(
        "✅ Диалог завершён.\n\n"
        "Если будут вопросы — обращайся!",
        reply_markup=user_ai_keyboard(),
    )


@router.message(UserAIStates.chatting)
async def handle_user_chat(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle user chat message."""
    user_message = message.text or ""
    if not user_message.strip():
        return

    # ========== SECURITY CHECKS ==========
    from app.services.aria_security_defense import (
        SECURITY_RESPONSE_BLOCKED,
        SECURITY_RESPONSE_FORWARDED,
        check_forwarded_message,
        get_security_guard,
        sanitize_user_input,
    )

    # Block forwarded messages
    forward_check = check_forwarded_message(message)
    if forward_check["is_forwarded"]:
        logger.warning(
            f"SECURITY: User {message.from_user.id} sent forwarded message"
        )
        await message.answer(
            SECURITY_RESPONSE_FORWARDED,
            parse_mode="Markdown",
            reply_markup=user_chat_keyboard(),
        )
        return

    # Check for security threats
    security_guard = get_security_guard()
    security_check = security_guard.check_message(
        text=user_message,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        is_admin=False,
    )

    if not security_check["allow"]:
        logger.error(
            f"🚨 SECURITY BLOCK: User {message.from_user.id} message blocked"
        )
        await message.answer(
            SECURITY_RESPONSE_BLOCKED,
            parse_mode="Markdown",
            reply_markup=user_chat_keyboard(),
        )
        return

    # Sanitize user input
    sanitized_message = sanitize_user_input(user_message)
    # ========== END SECURITY CHECKS ==========

    await message.answer("🤔 Секунду...")

    state_data = await state.get_data()
    history = state_data.get("conversation_history", [])

    ai_service = get_ai_service()

    user_data = {
        "ID": message.from_user.id,
        "Имя": message.from_user.first_name or "Пользователь",
    }

    response = await ai_service.chat(
        message=sanitized_message,  # Use sanitized input
        role=UserRole.USER,
        user_data=user_data,
        conversation_history=history,
    )

    history.append({"role": "user", "content": sanitized_message})
    history.append({"role": "assistant", "content": response})

    if len(history) > 16:
        history = history[-16:]

    await state.update_data(conversation_history=history)

    safe_response = sanitize_markdown(response)
    await safe_answer(
        message,
        safe_response,
        parse_mode="Markdown",
        reply_markup=user_chat_keyboard(),
    )

    logger.info(f"User AI chat {message.from_user.id}: {user_message[:30]}...")


@router.message(StateFilter("*"), F.text == "❓ Как работает платформа?")
async def explain_platform(
    message: Message,
    **data: Any,
) -> None:
    """Explain how platform works."""
    ai_service = get_ai_service()

    response = await ai_service.chat(
        message="Объясни простым языком как работает платформа ArbitroPLEX.",
        role=UserRole.USER,
    )

    safe_response = sanitize_markdown(response)
    await safe_answer(
        message,
        f"❓ **Как работает платформа**\n\n{safe_response}",
        parse_mode="Markdown",
        reply_markup=user_ai_keyboard(),
    )


@router.message(StateFilter("*"), F.text == "💰 Про депозиты")
async def explain_deposits(
    message: Message,
    **data: Any,
) -> None:
    """Explain deposits."""
    ai_service = get_ai_service()

    response = await ai_service.chat(
        message="Расскажи про депозиты: как сделать, минимальная сумма, как работает.",
        role=UserRole.USER,
    )

    safe_response = sanitize_markdown(response)
    await safe_answer(
        message,
        f"💰 **Про депозиты**\n\n{safe_response}",
        parse_mode="Markdown",
        reply_markup=user_ai_keyboard(),
    )


@router.message(StateFilter("*"), F.text == "💸 Про выводы")
async def explain_withdrawals(
    message: Message,
    **data: Any,
) -> None:
    """Explain withdrawals."""
    ai_service = get_ai_service()

    response = await ai_service.chat(
        message="Расскажи про вывод средств: как вывести, сроки, комиссии.",
        role=UserRole.USER,
    )

    safe_response = sanitize_markdown(response)
    await safe_answer(
        message,
        f"💸 **Про выводы**\n\n{safe_response}",
        parse_mode="Markdown",
        reply_markup=user_ai_keyboard(),
    )


@router.message(StateFilter("*"), F.text == "👥 Про рефералов")
async def explain_referrals(
    message: Message,
    **data: Any,
) -> None:
    """Explain referral program."""
    ai_service = get_ai_service()

    response = await ai_service.chat(
        message="Объясни реферальную программу: сколько уровней, какие бонусы.",
        role=UserRole.USER,
    )

    safe_response = sanitize_markdown(response)
    await safe_answer(
        message,
        f"👥 **Реферальная программа**\n\n{safe_response}",
        parse_mode="Markdown",
        reply_markup=user_ai_keyboard(),
    )
