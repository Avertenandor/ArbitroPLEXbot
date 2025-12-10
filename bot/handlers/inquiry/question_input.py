"""
Question input handlers for user inquiries.

This module handles the question input flow when users are creating
new inquiries.
"""

from typing import Any

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.inquiry_service import InquiryService
from bot.keyboards.user import (
    inquiry_waiting_keyboard,
    main_menu_reply_keyboard,
)
from bot.states.inquiry import InquiryStates

from .notifications import notify_admins_new_inquiry


router = Router(name="user_inquiry_question_input")


@router.message(InquiryStates.writing_question, F.text == "❌ Отмена")
async def handle_cancel_question(
    message: Message,
    state: FSMContext,
    user: User | None = None,
    **data: Any,
) -> None:
    """Cancel question input."""
    await state.clear()
    is_admin = data.get("is_admin", False)
    await message.answer(
        "❌ Отменено. Возвращаемся в главное меню.",
        reply_markup=main_menu_reply_keyboard(user=user, is_admin=is_admin),
    )


@router.message(InquiryStates.writing_question, F.text == "◀️ Главное меню")
async def handle_back_from_question(
    message: Message,
    state: FSMContext,
    user: User | None = None,
    **data: Any,
) -> None:
    """Return to main menu from question input."""
    await state.clear()
    is_admin = data.get("is_admin", False)
    await message.answer(
        "◀️ Главное меню",
        reply_markup=main_menu_reply_keyboard(user=user, is_admin=is_admin),
    )


@router.message(InquiryStates.writing_question)
async def handle_question_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    user: User | None = None,
    **data: Any,
) -> None:
    """Handle user's question text."""
    if not user:
        await state.clear()
        return

    question_text = message.text.strip()

    if len(question_text) < 10:
        await message.answer(
            "❌ Вопрос слишком короткий. "
            "Опишите проблему подробнее (минимум 10 символов).",
        )
        return

    if len(question_text) > 2000:
        await message.answer(
            "❌ Вопрос слишком длинный. "
            "Пожалуйста, сократите его до 2000 символов.",
        )
        return

    # Create inquiry
    inquiry_service = InquiryService(session)
    inquiry = await inquiry_service.create_inquiry(
        user_id=user.id,
        telegram_id=user.telegram_id,
        question_text=question_text,
    )

    await state.set_state(InquiryStates.in_dialog)
    await state.update_data(inquiry_id=inquiry.id)

    await message.answer(
        f"✅ Ваше обращение #{inquiry.id} создано!\n\n"
        "Администратор получит уведомление и свяжется с вами.\n"
        "Вы получите уведомление, когда администратор ответит.\n\n"
        "Вы можете дополнить свой вопрос, написав ещё одно сообщение.",
        reply_markup=inquiry_waiting_keyboard(),
    )

    # Notify admins about new inquiry
    await notify_admins_new_inquiry(bot, inquiry, session)
