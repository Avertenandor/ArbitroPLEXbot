"""
Admin Inquiry Details Handler.

Handles displaying detailed inquiry information and message history.
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_inquiry import InquiryStatus
from app.services.inquiry_service import InquiryService
from bot.keyboards.admin_keyboards import admin_inquiry_detail_keyboard
from bot.states.inquiry import AdminInquiryStates

router = Router(name="admin_inquiry_details")


# ============================================================================
# INQUIRY SELECTION (from list)
# ============================================================================


@router.message(AdminInquiryStates.viewing_list, F.text.startswith("📩 #"))
async def handle_select_inquiry(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Handle inquiry selection from list."""
    admin = data.get("admin")
    if not admin:
        await message.answer("❌ Доступ запрещён")
        return

    # Parse inquiry ID from button text: "📩 #123 username: preview..."
    try:
        text = message.text
        inquiry_id = int(text.split("#")[1].split()[0])
    except (ValueError, IndexError):
        await message.answer("❌ Не удалось определить номер обращения")
        return

    inquiry_service = InquiryService(session)
    inquiry = await inquiry_service.get_inquiry_with_messages(inquiry_id)

    if not inquiry:
        await message.answer("❌ Обращение не найдено")
        return

    await state.set_state(AdminInquiryStates.viewing_inquiry)
    await state.update_data(inquiry_id=inquiry_id)

    # Build message history
    username = inquiry.user.username or f"ID:{inquiry.telegram_id}"
    messages_text = ""
    if inquiry.messages:
        for msg in inquiry.messages:
            if msg.sender_type == "user":
                sender = f"👤 {username}"
            else:
                sender = "👨‍💼 Админ"
            time_str = msg.created_at.strftime("%d.%m %H:%M")
            messages_text += f"\n[{time_str}] {sender}:\n{msg.message_text}\n"

    status_emoji = {
        InquiryStatus.NEW.value: "🆕",
        InquiryStatus.IN_PROGRESS.value: "🔄",
        InquiryStatus.CLOSED.value: "✅",
    }

    is_assigned = inquiry.assigned_admin_id == admin.id

    await message.answer(
        f"📬 **Обращение #{inquiry.id}**\n"
        f"Статус: {status_emoji.get(inquiry.status, '')} {inquiry.status}\n"
        f"От: {username}\n"
        f"Создано: {inquiry.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"**Вопрос:**\n{inquiry.initial_question}\n"
        f"{messages_text}",
        parse_mode="Markdown",
        reply_markup=admin_inquiry_detail_keyboard(is_assigned=is_assigned),
    )
