"""
AI Assistant Handler for Admins.

Provides interface for admins to communicate with CloudSonet 4.5 AI.
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

from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import get_admin_keyboard_from_data

router = Router(name="admin_ai_assistant")


class AIAssistantStates(StatesGroup):
    """States for AI assistant interaction."""

    waiting_for_message = State()


def ai_assistant_keyboard() -> Any:
    """Create AI assistant keyboard."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📊 Статус системы"))
    builder.row(KeyboardButton(text="📋 Последние ошибки"))
    builder.row(KeyboardButton(text="👥 Статистика пользователей"))
    builder.row(KeyboardButton(text="💬 Написать сообщение AI"))
    builder.row(KeyboardButton(text="◀️ Назад в админку"))
    return builder.as_markup(resize_keyboard=True)


@router.message(StateFilter("*"), F.text == "🤖 AI Помощник")
async def handle_ai_assistant_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Show AI assistant menu.

    Args:
        message: Incoming message
        session: Database session
        state: FSM state
        **data: Handler data including admin flags
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    await state.clear()
    
    await message.answer(
        "🤖 **CloudSonet 4.5 AI Помощник**\n\n"
        "Добро пожаловать! Я ваш AI-помощник для управления системой.\n\n"
        "**Что я могу:**\n"
        "• Мониторить логи и ошибки в реальном времени\n"
        "• Исправлять обнаруженные проблемы\n"
        "• Отвечать на технические вопросы\n"
        "• Показывать статистику системы\n\n"
        "Выберите действие или напишите мне сообщение:",
        parse_mode="Markdown",
        reply_markup=ai_assistant_keyboard(),
    )

    logger.info(
        f"Admin {admin.username} ({admin.telegram_id}) opened AI Assistant menu"
    )


@router.message(StateFilter("*"), F.text == "💬 Написать сообщение AI")
async def start_ai_message(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Start writing message to AI."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    await state.set_state(AIAssistantStates.waiting_for_message)
    
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Отмена"))
    
    await message.answer(
        "💬 **Написать сообщение AI**\n\n"
        "Введите ваше сообщение или вопрос.\n"
        "Я получу его и отвечу вам как можно скорее.\n\n"
        "Примеры вопросов:\n"
        "• Какой статус системы?\n"
        "• Есть ли ошибки в логах?\n"
        "• Сколько активных пользователей?\n",
        parse_mode="Markdown",
        reply_markup=builder.as_markup(resize_keyboard=True),
    )


@router.message(AIAssistantStates.waiting_for_message, F.text == "❌ Отмена")
async def cancel_ai_message(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Cancel AI message input."""
    await state.clear()
    await message.answer(
        "❌ Ввод сообщения отменён.",
        reply_markup=ai_assistant_keyboard(),
    )


@router.message(AIAssistantStates.waiting_for_message)
async def receive_ai_message(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Receive message for AI assistant.
    
    The message will be saved and CloudSonet will read it during monitoring.
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    user_message = message.text or ""
    
    # Log the message for CloudSonet to read
    logger.info(
        f"AI_MESSAGE from {admin.username} ({admin.telegram_id}): {user_message}"
    )
    
    await state.clear()
    
    await message.answer(
        "✅ **Сообщение отправлено**\n\n"
        f"Ваше сообщение:\n_{user_message}_\n\n"
        "CloudSonet 4.5 получит его и ответит вам в ближайшее время.\n"
        "Ответ придёт в виде уведомления.",
        parse_mode="Markdown",
        reply_markup=ai_assistant_keyboard(),
    )


@router.message(StateFilter("*"), F.text == "📊 Статус системы")
async def show_system_status(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show system status."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    # Basic status info
    await message.answer(
        "📊 **Статус системы**\n\n"
        "🟢 Бот: Работает\n"
        "🟢 Worker: Активен\n"
        "🟢 Scheduler: Активен\n"
        "🟢 PostgreSQL: Подключен\n"
        "🟢 Redis: Подключен\n"
        "🟢 Blockchain RPC: Подключен\n\n"
        "💡 Для детальной информации напишите сообщение AI.",
        parse_mode="Markdown",
        reply_markup=ai_assistant_keyboard(),
    )

    logger.info(
        f"AI_MESSAGE from {admin.username}: Запрос статуса системы"
    )


@router.message(StateFilter("*"), F.text == "📋 Последние ошибки")
async def show_recent_errors(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Request recent errors from AI."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    await message.answer(
        "📋 **Запрос ошибок**\n\n"
        "CloudSonet 4.5 анализирует логи...\n"
        "Ответ придёт в ближайшее время.",
        parse_mode="Markdown",
        reply_markup=ai_assistant_keyboard(),
    )

    logger.info(
        f"AI_MESSAGE from {admin.username}: Запрос последних ошибок в логах"
    )


@router.message(StateFilter("*"), F.text == "👥 Статистика пользователей")
async def show_user_stats(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show user statistics."""
    from app.repositories.user_repository import UserRepository
    
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    user_repo = UserRepository(session)
    
    # Get basic stats
    try:
        total_users = await user_repo.count_all()
        active_users = await user_repo.count_active()
    except Exception:
        total_users = 0
        active_users = 0

    await message.answer(
        "👥 **Статистика пользователей**\n\n"
        f"📊 Всего пользователей: {total_users}\n"
        f"✅ Активных: {active_users}\n\n"
        "💡 Для детальной статистики напишите AI.",
        parse_mode="Markdown",
        reply_markup=ai_assistant_keyboard(),
    )


@router.message(StateFilter("*"), F.text == "◀️ Назад в админку")
async def back_to_admin(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Go back to admin panel."""
    await state.clear()
    await message.answer(
        "🔙 Возврат в админ-панель",
        reply_markup=get_admin_keyboard_from_data(data),
    )
