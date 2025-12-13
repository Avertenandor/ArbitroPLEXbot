"""
Admin Inquiry Response Handlers.

Handles admin responses to user inquiries:
- Text responses
- Photo responses
- Document responses
"""

from typing import Any

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.inquiry_service import InquiryService
from bot.keyboards.admin_keyboards import (
    admin_inquiry_detail_keyboard,
    admin_inquiry_response_keyboard,
)
from bot.states.inquiry import AdminInquiryStates


router = Router(name="admin_inquiry_responses")


# ============================================================================
# RESPOND TO USER
# ============================================================================


@router.message(
    AdminInquiryStates.viewing_inquiry,
    F.text == "💬 Ответить пользователю",
)
async def handle_start_response(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Start writing response to user."""
    await state.set_state(AdminInquiryStates.writing_response)
    await message.answer(
        "💬 Напишите ваш ответ пользователю:",
        reply_markup=admin_inquiry_response_keyboard(),
    )


@router.message(AdminInquiryStates.writing_response, F.text == "❌ Отмена")
async def handle_cancel_response(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Cancel response writing."""
    state_data = await state.get_data()
    _ = state_data.get("inquiry_id")  # Reserved for future use

    await state.set_state(AdminInquiryStates.viewing_inquiry)
    await message.answer(
        "❌ Отменено.",
        reply_markup=admin_inquiry_detail_keyboard(is_assigned=True),
    )


@router.message(
    AdminInquiryStates.writing_response,
    F.text == "◀️ Назад к обращению",
)
async def handle_back_to_inquiry(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Return to inquiry view."""
    await state.set_state(AdminInquiryStates.viewing_inquiry)
    await message.answer(
        "◀️ Возвращаемся к обращению.",
        reply_markup=admin_inquiry_detail_keyboard(is_assigned=True),
    )


# ============================================================================
# TEXT RESPONSE
# ============================================================================


@router.message(AdminInquiryStates.writing_response)
async def handle_response_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    **data: Any,
) -> None:
    """Handle admin response text."""
    admin = data.get("admin")
    if not admin:
        await message.answer("❌ Доступ запрещён")
        return

    state_data = await state.get_data()
    inquiry_id = state_data.get("inquiry_id")

    if not inquiry_id:
        from bot.utils.admin_utils import clear_state_preserve_admin_token

        await clear_state_preserve_admin_token(state)
        await message.answer("❌ Обращение не найдено")
        return

    inquiry_service = InquiryService(session)
    inquiry = await inquiry_service.get_inquiry_by_id(inquiry_id)

    if not inquiry:
        from bot.utils.admin_utils import clear_state_preserve_admin_token

        await clear_state_preserve_admin_token(state)
        await message.answer("❌ Обращение не найдено")
        return

    # Add admin message
    await inquiry_service.add_admin_message(
        inquiry_id=inquiry_id,
        admin_id=admin.id,
        message_text=message.text,
    )

    # Send to user
    try:
        await bot.send_message(
            inquiry.telegram_id,
            f"💬 **Ответ на ваше обращение #{inquiry_id}**\n\n"
            f"{message.text}\n\n"
            "Вы можете продолжить диалог, нажав «❓ Задать вопрос».",
            parse_mode="Markdown",
        )
        await message.answer(
            "✅ Ответ отправлен пользователю!",
            reply_markup=admin_inquiry_detail_keyboard(is_assigned=True),
        )
    except Exception as e:
        logger.error(f"Failed to send response to user: {e}")
        await message.answer(
            f"⚠️ Ответ сохранён, но не удалось доставить пользователю: {e}",
            reply_markup=admin_inquiry_detail_keyboard(is_assigned=True),
        )

    await state.set_state(AdminInquiryStates.viewing_inquiry)


# ============================================================================
# PHOTO RESPONSE
# ============================================================================


@router.message(AdminInquiryStates.writing_response, F.photo)
async def handle_admin_response_photo(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    **data: Any,
) -> None:
    """Handle admin photo response."""
    admin = data.get("admin")
    if not admin:
        return

    state_data = await state.get_data()
    inquiry_id = state_data.get("inquiry_id")

    if not inquiry_id:
        return

    inquiry_service = InquiryService(session)
    inquiry = await inquiry_service.get_inquiry_by_id(inquiry_id)

    if not inquiry:
        return

    caption = message.caption or "[Фото]"

    # Save reference
    await inquiry_service.add_admin_message(
        inquiry_id=inquiry_id,
        admin_id=admin.id,
        message_text=f"[📷 Фото] {caption}",
    )

    # Send to user
    try:
        await bot.send_photo(
            inquiry.telegram_id,
            photo=message.photo[-1].file_id,
            caption=f"📷 Ответ на обращение #{inquiry_id}\n\n{caption}",
        )
        await message.answer(
            "✅ Фото отправлено пользователю!",
            reply_markup=admin_inquiry_detail_keyboard(is_assigned=True),
        )
    except Exception as e:
        logger.error(f"Failed to send photo to user: {e}", exc_info=True)
        await message.answer("⚠️ Ошибка отправки фото. Пользователь мог заблокировать бота.")

    await state.set_state(AdminInquiryStates.viewing_inquiry)


# ============================================================================
# DOCUMENT RESPONSE
# ============================================================================


@router.message(AdminInquiryStates.writing_response, F.document)
async def handle_admin_response_document(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    **data: Any,
) -> None:
    """Handle admin document response."""
    admin = data.get("admin")
    if not admin:
        return

    state_data = await state.get_data()
    inquiry_id = state_data.get("inquiry_id")

    if not inquiry_id:
        return

    inquiry_service = InquiryService(session)
    inquiry = await inquiry_service.get_inquiry_by_id(inquiry_id)

    if not inquiry:
        return

    filename = message.document.file_name or "файл"

    # Save reference
    await inquiry_service.add_admin_message(
        inquiry_id=inquiry_id,
        admin_id=admin.id,
        message_text=f"[📄 Документ] {filename}",
    )

    # Send to user
    try:
        await bot.send_document(
            inquiry.telegram_id,
            document=message.document.file_id,
            caption=f"📄 Ответ на обращение #{inquiry_id}",
        )
        await message.answer(
            "✅ Документ отправлен пользователю!",
            reply_markup=admin_inquiry_detail_keyboard(is_assigned=True),
        )
    except Exception as e:
        logger.error(f"Failed to send document to user: {e}", exc_info=True)
        await message.answer("⚠️ Ошибка отправки документа. Пользователь мог заблокировать бота.")

    await state.set_state(AdminInquiryStates.viewing_inquiry)
