"""
Admin Inquiry Handlers.

Handles admin management of user inquiries (questions).
"""

from typing import Any

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_inquiry import InquiryStatus
from app.services.inquiry_service import InquiryService
from bot.keyboards.admin_keyboards import (
    admin_inquiry_detail_keyboard,
    admin_inquiry_list_keyboard,
    admin_inquiry_menu_keyboard,
    admin_inquiry_response_keyboard,
    admin_keyboard,
)
from bot.states.inquiry import AdminInquiryStates

router = Router(name="admin_inquiry")


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
        await message.answer(
            "📋 У вас нет активных обращений в работе.\n\n"
            "Возьмите новое обращение из списка «📬 Новые обращения».",
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
            sender = f"👤 {username}" if msg.sender_type == "user" else "👨‍💼 Админ"
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


# ============================================================================
# TAKE INQUIRY
# ============================================================================


@router.message(AdminInquiryStates.viewing_inquiry, F.text == "✋ Взять в работу")
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
    inquiry_id = state_data.get("inquiry_id")

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
        await state.clear()
        await message.answer("❌ Обращение не найдено")
        return

    inquiry_service = InquiryService(session)
    inquiry = await inquiry_service.get_inquiry_by_id(inquiry_id)

    if not inquiry:
        await state.clear()
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
        logger.error(f"Failed to send photo to user: {e}")
        await message.answer(f"⚠️ Ошибка отправки: {e}")

    await state.set_state(AdminInquiryStates.viewing_inquiry)


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
        logger.error(f"Failed to send document to user: {e}")
        await message.answer(f"⚠️ Ошибка отправки: {e}")

    await state.set_state(AdminInquiryStates.viewing_inquiry)


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


# ============================================================================
# NAVIGATION
# ============================================================================


@router.message(StateFilter("*"), F.text == "◀️ Назад к списку")
async def handle_back_to_list(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Return to inquiry list."""
    is_admin = data.get("is_admin", False)
    if not is_admin:
        return

    state_data = await state.get_data()
    inquiry_type = state_data.get("inquiry_type", "new")

    # Redirect to appropriate list
    if inquiry_type == "my":
        await handle_my_inquiries(message, state, session, **data)
    elif inquiry_type == "closed":
        await handle_closed_inquiries(message, state, session, **data)
    else:
        await handle_new_inquiries(message, state, session, **data)


@router.message(StateFilter("*"), F.text == "◀️ Назад к обращениям")
async def handle_back_to_inquiries_menu(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Return to inquiries main menu."""
    await handle_admin_inquiries_menu(message, state, session, **data)


@router.message(StateFilter("*"), F.text == "🔄 Обновить список")
async def handle_refresh_list(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Refresh current inquiry list."""
    state_data = await state.get_data()
    inquiry_type = state_data.get("inquiry_type", "new")

    if inquiry_type == "my":
        await handle_my_inquiries(message, state, session, **data)
    elif inquiry_type == "closed":
        await handle_closed_inquiries(message, state, session, **data)
    else:
        await handle_new_inquiries(message, state, session, **data)
