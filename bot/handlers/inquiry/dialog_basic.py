"""
Basic dialog action handlers for user inquiries.

This module handles basic dialog actions like viewing history, canceling,
closing inquiries, and navigating back to the main menu.
"""

from typing import Any

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_inquiry import InquiryStatus
from app.services.inquiry_service import InquiryService
from bot.keyboards.user import (
    inquiry_dialog_keyboard,
    inquiry_history_keyboard,
    main_menu_reply_keyboard,
)
from bot.states.inquiry import InquiryStates

router = Router(name="user_inquiry_dialog_basic")


@router.message(InquiryStates.in_dialog, F.text == "📜 Мои обращения")
async def handle_my_inquiries_user(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User | None = None,
    **data: Any,
) -> None:
    """Show user's inquiry history."""
    if not user:
        return

    inquiry_service = InquiryService(session)
    inquiries = await inquiry_service.get_user_inquiries(user.id)

    if not inquiries:
        await message.answer(
            "📜 У вас пока нет обращений.\n\n"
            "Нажмите «❓ Задать вопрос» чтобы создать первое обращение.",
            reply_markup=inquiry_history_keyboard(),
        )
        return

    text = "📜 **Ваши обращения:**\n\n"
    for inq in inquiries[:10]:  # Last 10
        status_emoji = {
            InquiryStatus.NEW.value: "🆕",
            InquiryStatus.IN_PROGRESS.value: "🔄",
            InquiryStatus.CLOSED.value: "✅",
        }
        date_str = inq.created_at.strftime("%d.%m.%Y")
        preview = inq.initial_question[:40]
        if len(inq.initial_question) > 40:
            preview += "..."
        text += (
            f"{status_emoji.get(inq.status, '❓')} "
            f"#{inq.id} ({date_str})\n{preview}\n\n"
        )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=inquiry_history_keyboard(),
    )


@router.message(InquiryStates.in_dialog, F.text == "📝 Дополнить вопрос")
async def handle_add_to_question(
    message: Message,
    **data: Any,
) -> None:
    """Prompt user to add more to their question."""
    await message.answer(
        "📝 Напишите дополнение к вашему вопросу:",
    )


@router.message(InquiryStates.in_dialog, F.text == "❌ Отменить обращение")
async def handle_cancel_inquiry(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User | None = None,
    **data: Any,
) -> None:
    """Cancel/close inquiry by user."""
    state_data = await state.get_data()
    inquiry_id = state_data.get("inquiry_id")

    if inquiry_id:
        inquiry_service = InquiryService(session)
        await inquiry_service.close_inquiry(inquiry_id, closed_by="user")

    await state.clear()
    is_admin = data.get("is_admin", False)
    await message.answer(
        "✅ Обращение закрыто. Спасибо за обратную связь!",
        reply_markup=main_menu_reply_keyboard(user=user, is_admin=is_admin),
    )


@router.message(InquiryStates.in_dialog, F.text == "✅ Закрыть обращение")
async def handle_close_inquiry(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    user: User | None = None,
    **data: Any,
) -> None:
    """Close active inquiry by user."""
    state_data = await state.get_data()
    inquiry_id = state_data.get("inquiry_id")

    if inquiry_id:
        inquiry_service = InquiryService(session)
        inquiry = await inquiry_service.get_inquiry_with_messages(inquiry_id)

        await inquiry_service.close_inquiry(inquiry_id, closed_by="user")

        # Notify admin if assigned
        if inquiry and inquiry.assigned_admin_id:
            try:
                from app.repositories.admin_repository import AdminRepository
                admin_repo = AdminRepository(session)
                admin = await admin_repo.get_by_id(inquiry.assigned_admin_id)
                if admin:
                    await bot.send_message(
                        admin.telegram_id,
                        f"ℹ️ Пользователь закрыл обращение #{inquiry_id}.",
                    )
            except Exception as e:
                logger.error(f"Failed to notify admin: {e}")

    await state.clear()
    is_admin = data.get("is_admin", False)
    await message.answer(
        "✅ Обращение успешно закрыто. Спасибо!",
        reply_markup=main_menu_reply_keyboard(user=user, is_admin=is_admin),
    )


@router.message(InquiryStates.in_dialog, F.text == "◀️ Главное меню")
async def handle_back_from_dialog(
    message: Message,
    state: FSMContext,
    user: User | None = None,
    **data: Any,
) -> None:
    """Return to main menu (inquiry stays active)."""
    await state.clear()
    is_admin = data.get("is_admin", False)
    await message.answer(
        "◀️ Главное меню\n\n"
        "Ваше обращение остаётся активным. "
        "Вы получите уведомление, когда администратор ответит.",
        reply_markup=main_menu_reply_keyboard(user=user, is_admin=is_admin),
    )
