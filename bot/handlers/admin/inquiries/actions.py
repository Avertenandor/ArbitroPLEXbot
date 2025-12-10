"""
Admin Inquiry Actions Handlers.

Handles admin actions on inquiries:
- Take inquiry (assign to admin)
- Close inquiry
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
    admin_inquiry_menu_keyboard,
)
from bot.states.inquiry import AdminInquiryStates


router = Router(name="admin_inquiry_actions")


# ============================================================================
# TAKE INQUIRY
# ============================================================================


@router.message(
    AdminInquiryStates.viewing_inquiry, F.text == "✋ Взять в работу"
)
async def handle_take_inquiry(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    **data: Any,
) -> None:
    """Assign inquiry to current admin."""
    admin = data.get("admin")
    if not admin:
        await message.answer("❌ Доступ запрещён")
        return

    state_data = await state.get_data()
    inquiry_id = state_data.get("inquiry_id")

    if not inquiry_id:
        await message.answer("❌ Обращение не найдено")
        return

    inquiry_service = InquiryService(session)
    inquiry = await inquiry_service.assign_to_admin(inquiry_id, admin.id)

    if not inquiry:
        await message.answer(
            "❌ Не удалось взять обращение. "
            "Возможно, оно уже взято другим администратором.",
            reply_markup=admin_inquiry_menu_keyboard(),
        )
        await state.clear()
        return

    # Notify user
    try:
        await bot.send_message(
            inquiry.telegram_id,
            f"✅ Ваше обращение #{inquiry_id} принято в работу!\n\n"
            "Администратор скоро ответит вам.",
        )
    except Exception as e:
        logger.warning(f"Failed to notify user: {e}")

    await message.answer(
        f"✅ Обращение #{inquiry_id} взято в работу!\n\n"
        "Теперь вы можете ответить пользователю.",
        reply_markup=admin_inquiry_detail_keyboard(is_assigned=True),
    )


# ============================================================================
# CLOSE INQUIRY (by admin)
# ============================================================================


@router.message(
    AdminInquiryStates.viewing_inquiry,
    F.text == "✅ Закрыть обращение",
)
async def handle_admin_close_inquiry(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    **data: Any,
) -> None:
    """Close inquiry by admin."""
    state_data = await state.get_data()
    inquiry_id = state_data.get("inquiry_id")

    if not inquiry_id:
        await message.answer("❌ Обращение не найдено")
        return

    inquiry_service = InquiryService(session)
    inquiry = await inquiry_service.get_inquiry_by_id(inquiry_id)

    if inquiry:
        await inquiry_service.close_inquiry(inquiry_id, closed_by="admin")

        # Notify user
        try:
            await bot.send_message(
                inquiry.telegram_id,
                f"✅ Ваше обращение #{inquiry_id} закрыто администратором.\n\n"
                "Если у вас остались вопросы, создайте новое обращение.",
            )
        except Exception as e:
            logger.warning(f"Failed to notify user: {e}")

    await state.clear()
    await message.answer(
        f"✅ Обращение #{inquiry_id} закрыто.",
        reply_markup=admin_inquiry_menu_keyboard(),
    )
