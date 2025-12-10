"""
Admin Inquiry Menu Handler.

Handles the main entry point for admin inquiry management.
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_inquiry import InquiryStatus
from app.services.inquiry_service import InquiryService
from bot.keyboards.admin_keyboards import admin_inquiry_menu_keyboard


router = Router(name="admin_inquiry_menu")


# ============================================================================
# MAIN ENTRY POINT: "📨 Обращения от пользователей"
# ============================================================================


@router.message(StateFilter("*"), F.text == "📨 Обращения от пользователей")
async def handle_admin_inquiries_menu(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show admin inquiries menu."""
    is_admin = data.get("is_admin", False)
    admin = data.get("admin")
    if not is_admin:
        await message.answer("❌ Доступ запрещён")
        return

    await state.clear()

    # Get counts
    inquiry_service = InquiryService(session)
    new_count = await inquiry_service.count_new_inquiries()

    # Count admin's active inquiries
    my_count = 0
    if admin:
        my_inquiries = await inquiry_service.get_admin_inquiries(
            admin.id,
            status=InquiryStatus.IN_PROGRESS.value,
        )
        my_count = len(my_inquiries)

    await message.answer(
        "📨 **Обращения от пользователей**\n\n"
        f"📬 Новых обращений: {new_count}\n"
        f"📋 Моих в работе: {my_count}\n\n"
        "Выберите раздел:",
        parse_mode="Markdown",
        reply_markup=admin_inquiry_menu_keyboard(),
    )
