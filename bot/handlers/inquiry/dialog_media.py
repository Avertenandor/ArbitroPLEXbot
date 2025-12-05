"""
Media handlers for user inquiry dialogs.

This module handles photos and documents sent by users in inquiry dialogs.
Media files are forwarded to the assigned admin and logged in the inquiry.
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
from bot.keyboards.user import inquiry_dialog_keyboard
from bot.states.inquiry import InquiryStates

router = Router(name="user_inquiry_dialog_media")


@router.message(InquiryStates.in_dialog, F.photo)
async def handle_dialog_photo(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    user: User | None = None,
    **data: Any,
) -> None:
    """Handle photo in dialog - forward to admin."""
    if not user:
        return

    state_data = await state.get_data()
    inquiry_id = state_data.get("inquiry_id")

    if not inquiry_id:
        return

    inquiry_service = InquiryService(session)
    inquiry = await inquiry_service.get_inquiry_by_id(inquiry_id)

    if not inquiry or inquiry.status == InquiryStatus.CLOSED.value:
        return

    caption = message.caption or "[Фото без подписи]"

    # Save text reference
    await inquiry_service.add_user_message(
        inquiry_id=inquiry_id,
        user_id=user.id,
        message_text=f"[📷 Фото] {caption}",
    )

    # Forward photo to admin if assigned
    if inquiry.assigned_admin_id:
        try:
            from app.repositories.admin_repository import AdminRepository
            admin_repo = AdminRepository(session)
            admin = await admin_repo.get_by_id(inquiry.assigned_admin_id)
            if admin:
                username = user.username or f"ID:{user.telegram_id}"
                await bot.send_photo(
                    admin.telegram_id,
                    photo=message.photo[-1].file_id,
                    caption=(
                        f"📷 Фото в обращении #{inquiry_id}\n"
                        f"От: {username}\n\n{caption}"
                    ),
                )
        except Exception as e:
            logger.error(f"Failed to forward photo to admin: {e}")

    await message.answer(
        "✅ Фото отправлено администратору.",
        reply_markup=inquiry_dialog_keyboard(),
    )


@router.message(InquiryStates.in_dialog, F.document)
async def handle_dialog_document(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    user: User | None = None,
    **data: Any,
) -> None:
    """Handle document in dialog - forward to admin."""
    if not user:
        return

    state_data = await state.get_data()
    inquiry_id = state_data.get("inquiry_id")

    if not inquiry_id:
        return

    inquiry_service = InquiryService(session)
    inquiry = await inquiry_service.get_inquiry_by_id(inquiry_id)

    if not inquiry or inquiry.status == InquiryStatus.CLOSED.value:
        return

    filename = message.document.file_name or "файл"

    # Save text reference
    await inquiry_service.add_user_message(
        inquiry_id=inquiry_id,
        user_id=user.id,
        message_text=f"[📄 Документ] {filename}",
    )

    # Forward document to admin if assigned
    if inquiry.assigned_admin_id:
        try:
            from app.repositories.admin_repository import AdminRepository
            admin_repo = AdminRepository(session)
            admin = await admin_repo.get_by_id(inquiry.assigned_admin_id)
            if admin:
                username = user.username or f"ID:{user.telegram_id}"
                await bot.send_document(
                    admin.telegram_id,
                    document=message.document.file_id,
                    caption=(
                        f"📄 Документ в обращении #{inquiry_id}\n"
                        f"От: {username}"
                    ),
                )
        except Exception as e:
            logger.error(f"Failed to forward document to admin: {e}")

    await message.answer(
        "✅ Документ отправлен администратору.",
        reply_markup=inquiry_dialog_keyboard(),
    )
