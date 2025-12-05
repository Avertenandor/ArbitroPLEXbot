"""
Text message handlers for user inquiry dialogs.

This module handles text messages sent by users in active inquiry dialogs,
forwarding them to assigned admins and saving them to the database.
"""

from typing import Any

from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_inquiry import InquiryStatus
from app.services.inquiry_service import InquiryService
from bot.keyboards.user import (
    inquiry_dialog_keyboard,
    inquiry_waiting_keyboard,
    main_menu_reply_keyboard,
)
from bot.states.inquiry import InquiryStates

router = Router(name="user_inquiry_dialog_messages")


@router.message(InquiryStates.in_dialog)
async def handle_dialog_message(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    user: User | None = None,
    **data: Any,
) -> None:
    """Handle user message in active dialog."""
    if not user:
        return

    state_data = await state.get_data()
    inquiry_id = state_data.get("inquiry_id")

    if not inquiry_id:
        await state.clear()
        is_admin = data.get("is_admin", False)
        await message.answer(
            "❌ Обращение не найдено. Попробуйте создать новое.",
            reply_markup=main_menu_reply_keyboard(
                user=user, is_admin=is_admin
            ),
        )
        return

    inquiry_service = InquiryService(session)
    inquiry = await inquiry_service.get_inquiry_with_messages(inquiry_id)

    if not inquiry or inquiry.status == InquiryStatus.CLOSED.value:
        await state.clear()
        is_admin = data.get("is_admin", False)
        await message.answer(
            "❌ Это обращение уже закрыто. Создайте новое при необходимости.",
            reply_markup=main_menu_reply_keyboard(
                user=user, is_admin=is_admin
            ),
        )
        return

    # Add user message
    await inquiry_service.add_user_message(
        inquiry_id=inquiry_id,
        user_id=user.id,
        message_text=message.text,
    )

    if inquiry.status == InquiryStatus.NEW.value:
        await message.answer(
            "✅ Сообщение добавлено к вашему обращению.",
            reply_markup=inquiry_waiting_keyboard(),
        )
    else:
        # Notify admin about new message
        if inquiry.assigned_admin_id:
            try:
                from app.repositories.admin_repository import AdminRepository
                admin_repo = AdminRepository(session)
                admin = await admin_repo.get_by_id(inquiry.assigned_admin_id)
                if admin:
                    username = user.username or f"ID:{user.telegram_id}"
                    await bot.send_message(
                        admin.telegram_id,
                        f"💬 Новое сообщение в обращении #{inquiry_id}\n"
                        f"От: {username}\n\n"
                        f"{message.text}",
                    )
            except Exception as e:
                logger.error(f"Failed to notify admin: {e}")

        await message.answer(
            "✅ Сообщение отправлено администратору.",
            reply_markup=inquiry_dialog_keyboard(),
        )
