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
from app.services.ai_assistant_service import UserRole, get_ai_service
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import get_admin_keyboard_from_data

router = Router(name="admin_ai_assistant")


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
    builder.row(KeyboardButton(text="🔚 Завершить диалог"))
    return builder.as_markup(resize_keyboard=True)


async def get_platform_stats(session: AsyncSession) -> dict[str, Any]:
    """Get platform statistics for AI context."""
    try:
        user_repo = UserRepository(session)
        total_users = await user_repo.count_all()
        active_users = await user_repo.count_active()

        return {
            "Всего пользователей": total_users,
            "Активных пользователей": active_users,
        }
    except Exception as e:
        logger.error(f"Error getting platform stats: {e}")
        return {}


def get_user_role_from_admin(admin: Any) -> UserRole:
    """Convert admin model to UserRole."""
    if admin.is_super_admin:
        return UserRole.SUPER_ADMIN
    elif admin.is_extended_admin:
        return UserRole.EXTENDED_ADMIN
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

    await state.clear()

    ai_service = get_ai_service()
    status = "🟢 Онлайн" if ai_service.is_available() else "🔴 Недоступен"

    await message.answer(
        f"🤖 **AI Помощник CloudSonet**\n\n"
        f"Статус: {status}\n\n"
        f"Привет, {admin.display_name}! Я твой интеллектуальный помощник.\n\n"
        f"**Что я умею:**\n"
        f"• Отвечать на вопросы о работе платформы\n"
        f"• Помогать с админ-функциями\n"
        f"• Давать советы и рекомендации\n"
        f"• Объяснять сложные вещи простым языком\n\n"
        f"Выбери действие или начни свободный диалог:",
        parse_mode="Markdown",
        reply_markup=ai_assistant_keyboard(),
    )

    logger.info(f"Admin {admin.username} opened AI Assistant")


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
    state: FSMContext,
    **data: Any,
) -> None:
    """End chat mode."""
    await state.clear()
    await message.answer(
        "✅ Диалог завершён.\n\n"
        "Было приятно пообщаться! Возвращайся, если будут вопросы.",
        reply_markup=ai_assistant_keyboard(),
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

    # Admin context
    admin_data = {
        "Имя": admin.display_name,
        "Роль": admin.role_display,
        "ID": admin.telegram_id,
    }

    # Get AI response
    response = await ai_service.chat(
        message=user_message,
        role=role,
        user_data=admin_data,
        platform_stats=platform_stats,
        conversation_history=history,
    )

    # Update history
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": response})

    # Keep only last 20 messages
    if len(history) > 20:
        history = history[-20:]

    await state.update_data(conversation_history=history)

    await message.answer(
        response,
        parse_mode="Markdown",
        reply_markup=chat_keyboard(),
    )

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
    platform_stats = await get_platform_stats(session)

    response = await ai_service.chat(
        message="Дай краткий отчёт о статусе системы.",
        role=role,
        platform_stats=platform_stats,
    )

    await message.answer(
        f"📊 **Статус системы**\n\n{response}",
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

    stats = await get_platform_stats(session)

    text = "👥 **Статистика платформы**\n\n"
    for key, value in stats.items():
        text += f"• {key}: **{value}**\n"

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

    await message.answer(
        f"❓ **Справка по админ-панели**\n\n{response}",
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

    await message.answer(
        f"📚 **Частые вопросы**\n\n{response}",
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
    await state.clear()
    await message.answer(
        "👑 Возвращаюсь в админ-панель...",
        reply_markup=get_admin_keyboard_from_data(data),
    )
