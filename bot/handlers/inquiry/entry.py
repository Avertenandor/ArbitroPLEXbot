"""
Entry point handler for user inquiries.

This module handles the "❓ Задать вопрос" button - the main entry point
for users to create and view their active inquiries.
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_inquiry import InquiryStatus
from app.services.inquiry_service import InquiryService
from bot.keyboards.user import (
    inquiry_dialog_keyboard,
    inquiry_input_keyboard,
    inquiry_waiting_keyboard,
)
from bot.states.inquiry import InquiryStates

router = Router(name="user_inquiry_entry")


@router.message(StateFilter("*"), F.text == "❓ Задать вопрос")
async def handle_ask_question(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User | None = None,
    **data: Any,
) -> None:
    """Handle 'Ask Question' button - entry point for user inquiries."""
    if not user:
        await message.answer(
            "❌ Эта функция доступна только "
            "зарегистрированным пользователям.\n"
            "Пожалуйста, пройдите регистрацию.",
        )
        return

    # Check if user has active inquiry
    inquiry_service = InquiryService(session)
    active_inquiry = await inquiry_service.get_user_active_inquiry(user.id)

    if active_inquiry:
        # User has active inquiry - show its status
        if active_inquiry.status == InquiryStatus.NEW.value:
            await message.answer(
                "📬 У вас уже есть активное обращение, ожидающее ответа.\n\n"
                f"**Ваш вопрос:**\n{active_inquiry.initial_question}\n\n"
                "Как только администратор возьмёт его в работу, "
                "вы получите уведомление.",
                parse_mode="Markdown",
                reply_markup=inquiry_waiting_keyboard(),
            )
            await state.set_state(InquiryStates.in_dialog)
            await state.update_data(inquiry_id=active_inquiry.id)

        elif active_inquiry.status == InquiryStatus.IN_PROGRESS.value:
            # Show dialog with admin
            admin_name = "Администратор"
            if active_inquiry.assigned_admin:
                admin_name = (
                    active_inquiry.assigned_admin.username
                    or f"Админ #{active_inquiry.assigned_admin_id}"
                )

            # Build message history
            messages_text = ""
            if active_inquiry.messages:
                for msg in active_inquiry.messages[-5:]:  # Last 5 messages
                    if msg.sender_type == "user":
                        sender = "👤 Вы"
                    else:
                        sender = f"👨‍💼 {admin_name}"
                    messages_text += f"\n{sender}: {msg.message_text}\n"

            await message.answer(
                f"💬 У вас активный диалог с {admin_name}.\n\n"
                f"**Ваш вопрос:**\n{active_inquiry.initial_question}\n"
                f"{messages_text}\n"
                "Напишите сообщение, оно будет отправлено администратору.",
                parse_mode="Markdown",
                reply_markup=inquiry_dialog_keyboard(),
            )
            await state.set_state(InquiryStates.in_dialog)
            await state.update_data(inquiry_id=active_inquiry.id)
        return

    # No active inquiry - prompt user to write question
    await message.answer(
        "❓ **Задать вопрос**\n\n"
        "Напишите ваш вопрос, и он будет передан администратору.\n"
        "Вы получите уведомление, когда администратор ответит.\n\n"
        "📝 Введите ваш вопрос:",
        parse_mode="Markdown",
        reply_markup=inquiry_input_keyboard(),
    )
    await state.set_state(InquiryStates.writing_question)


@router.message(StateFilter("*"), F.text == "❓ Задать новый вопрос")
async def handle_new_question_shortcut(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User | None = None,
    **data: Any,
) -> None:
    """Shortcut to create new question from history view."""
    await handle_ask_question(message, state, session, user, **data)
