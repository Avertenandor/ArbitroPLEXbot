"""
User Inquiry Handlers.

Handles user questions to admins via "Задать вопрос" button.
"""

from typing import Any

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_inquiry import InquiryStatus
from app.services.inquiry_service import InquiryService
from bot.keyboards.user_keyboards import (
    inquiry_dialog_keyboard,
    inquiry_history_keyboard,
    inquiry_input_keyboard,
    inquiry_waiting_keyboard,
    main_menu_reply_keyboard,
)
from bot.states.inquiry import InquiryStates

router = Router(name="user_inquiry")


# ============================================================================
# MAIN ENTRY POINT: "❓ Задать вопрос"
# ============================================================================


@router.message(StateFilter("*"), F.text == "❓ Задать вопрос")
async def handle_ask_question(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User | None = None,
    **data: Any,
) -> None:
    """Handle 'Ask Question' button - entry point for user inquiries."""
    if not user:
        await message.answer(
            "❌ Эта функция доступна только "
            "зарегистрированным пользователям.\n"
            "Пожалуйста, пройдите регистрацию.",
        )
        return

    # Check if user has active inquiry
    inquiry_service = InquiryService(session)
    active_inquiry = await inquiry_service.get_user_active_inquiry(user.id)

    if active_inquiry:
        # User has active inquiry - show its status
        if active_inquiry.status == InquiryStatus.NEW.value:
            await message.answer(
                "📬 У вас уже есть активное обращение, ожидающее ответа.\n\n"
                f"**Ваш вопрос:**\n{active_inquiry.initial_question}\n\n"
                "Как только администратор возьмёт его в работу, "
                "вы получите уведомление.",
                parse_mode="Markdown",
                reply_markup=inquiry_waiting_keyboard(),
            )
            await state.set_state(InquiryStates.in_dialog)
            await state.update_data(inquiry_id=active_inquiry.id)

        elif active_inquiry.status == InquiryStatus.IN_PROGRESS.value:
            # Show dialog with admin
            admin_name = "Администратор"
            if active_inquiry.assigned_admin:
                admin_name = (
                    active_inquiry.assigned_admin.username
                    or f"Админ #{active_inquiry.assigned_admin_id}"
                )

            # Build message history
            messages_text = ""
            if active_inquiry.messages:
                for msg in active_inquiry.messages[-5:]:  # Last 5 messages
                    if msg.sender_type == "user":
                        sender = "👤 Вы"
                    else:
                        sender = f"👨‍💼 {admin_name}"
                    messages_text += f"\n{sender}: {msg.message_text}\n"

            await message.answer(
                f"💬 У вас активный диалог с {admin_name}.\n\n"
                f"**Ваш вопрос:**\n{active_inquiry.initial_question}\n"
                f"{messages_text}\n"
                "Напишите сообщение, оно будет отправлено администратору.",
                parse_mode="Markdown",
                reply_markup=inquiry_dialog_keyboard(),
            )
            await state.set_state(InquiryStates.in_dialog)
            await state.update_data(inquiry_id=active_inquiry.id)
        return

    # No active inquiry - prompt user to write question
    await message.answer(
        "❓ **Задать вопрос**\n\n"
        "Напишите ваш вопрос, и он будет передан администратору.\n"
        "Вы получите уведомление, когда администратор ответит.\n\n"
        "📝 Введите ваш вопрос:",
        parse_mode="Markdown",
        reply_markup=inquiry_input_keyboard(),
    )
    await state.set_state(InquiryStates.writing_question)


# ============================================================================
# QUESTION INPUT
# ============================================================================


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


# ============================================================================
# DIALOG FLOW
# ============================================================================


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


@router.message(StateFilter("*"), F.text == "❓ Задать новый вопрос")
async def handle_new_question_shortcut(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User | None = None,
    **data: Any,
) -> None:
    """Shortcut to create new question from history view."""
    await handle_ask_question(message, state, session, user, **data)


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


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def notify_admins_new_inquiry(
    bot: Bot,
    inquiry,
    session: AsyncSession,
) -> None:
    """Уведомить админов о новом обращении."""
    try:
        from app.services.admin_event_monitor import (
            AdminEventMonitor,
            EventCategory,
            EventPriority,
        )

        username = "нет"
        if inquiry.user:
            username = inquiry.user.username or f"ID:{inquiry.telegram_id}"

        preview = inquiry.initial_question[:100]
        if len(inquiry.initial_question) > 100:
            preview += "..."

        monitor = AdminEventMonitor(bot, session)
        await monitor.notify(
            category=EventCategory.INQUIRY,
            priority=EventPriority.MEDIUM,
            title="Новый вопрос от пользователя",
            details={
                "ID обращения": inquiry.id,
                "Пользователь": f"@{username}",
                "Telegram ID": inquiry.telegram_id,
                "Вопрос": preview,
            },
            footer="Откройте «📨 Обращения» в админ-панели",
        )

    except Exception as e:
        logger.error(f"Ошибка уведомления админов о вопросе: {e}")

