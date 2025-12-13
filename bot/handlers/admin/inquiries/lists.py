"""
Admin Inquiry Lists Handlers.

Handles displaying different inquiry lists:
- New inquiries (not assigned)
- My inquiries (assigned to current admin)
- Closed inquiries
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_inquiry import InquiryStatus
from app.services.inquiry_service import InquiryService
from bot.keyboards.admin_keyboards import (
    admin_inquiry_list_keyboard,
    admin_inquiry_menu_keyboard,
)
from bot.states.inquiry import AdminInquiryStates


router = Router(name="admin_inquiry_lists")


# ============================================================================
# NEW INQUIRIES LIST
# ============================================================================


@router.message(StateFilter("*"), F.text == "📬 Новые обращения")
async def handle_new_inquiries(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show list of new inquiries waiting for admin."""
    is_admin = data.get("is_admin", False)
    if not is_admin:
        await message.answer("❌ Доступ запрещён")
        return

    inquiry_service = InquiryService(session)
    inquiries = await inquiry_service.get_new_inquiries()

    if not inquiries:
        await message.answer(
            "📭 Нет новых обращений.\n\n"
            "Все вопросы пользователей обработаны!",
            reply_markup=admin_inquiry_menu_keyboard(),
        )
        return

    await state.set_state(AdminInquiryStates.viewing_list)
    await state.update_data(inquiry_type="new")

    await message.answer(
        f"📬 **Новые обращения** ({len(inquiries)})\n\n"
        "Выберите обращение для просмотра:",
        parse_mode="Markdown",
        reply_markup=admin_inquiry_list_keyboard(inquiries),
    )


# ============================================================================
# MY INQUIRIES (Assigned to current admin)
# ============================================================================


@router.message(StateFilter("*"), F.text == "📋 Мои обращения")
async def handle_my_inquiries(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show inquiries assigned to current admin."""
    is_admin = data.get("is_admin", False)
    admin = data.get("admin")
    if not is_admin or not admin:
        await message.answer("❌ Доступ запрещён")
        return

    inquiry_service = InquiryService(session)
    inquiries = await inquiry_service.get_admin_inquiries(
        admin.id,
        status=InquiryStatus.IN_PROGRESS.value,
    )

    if not inquiries:
        no_inquiries_msg = (
            "📋 У вас нет активных обращений в работе.\n\n"
            "Возьмите новое обращение из списка "
            "«📬 Новые обращения»."
        )
        await message.answer(
            no_inquiries_msg,
            reply_markup=admin_inquiry_menu_keyboard(),
        )
        return

    await state.set_state(AdminInquiryStates.viewing_list)
    await state.update_data(inquiry_type="my")

    await message.answer(
        f"📋 **Мои обращения** ({len(inquiries)})\n\n"
        "Выберите обращение:",
        parse_mode="Markdown",
        reply_markup=admin_inquiry_list_keyboard(inquiries),
    )


# ============================================================================
# CLOSED INQUIRIES
# ============================================================================


@router.message(StateFilter("*"), F.text == "✅ Закрытые обращения")
async def handle_closed_inquiries(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show closed inquiries."""
    is_admin = data.get("is_admin", False)
    admin = data.get("admin")
    if not is_admin or not admin:
        await message.answer("❌ Доступ запрещён")
        return

    inquiry_service = InquiryService(session)
    inquiries = await inquiry_service.get_admin_inquiries(
        admin.id,
        status=InquiryStatus.CLOSED.value,
    )

    if not inquiries:
        await message.answer(
            "✅ Нет закрытых обращений.",
            reply_markup=admin_inquiry_menu_keyboard(),
        )
        return

    await state.set_state(AdminInquiryStates.viewing_list)
    await state.update_data(inquiry_type="closed")

    await message.answer(
        f"✅ **Закрытые обращения** ({len(inquiries)})\n\n"
        "Выберите для просмотра:",
        parse_mode="Markdown",
        reply_markup=admin_inquiry_list_keyboard(inquiries),
    )
