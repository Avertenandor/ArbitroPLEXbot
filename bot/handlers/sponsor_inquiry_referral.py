"""
Sponsor Inquiry Handlers - Referral Side.

Handles referral's questions to their sponsor.
"""

from typing import Any

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sponsor_inquiry import SponsorInquiryStatus
from app.models.user import User
from app.services.sponsor_inquiry_service import (
    SponsorInquiryService,
    notify_sponsor_new_inquiry,
)
from bot.keyboards.reply import referral_keyboard
from bot.states.sponsor_inquiry import SponsorInquiryStates


router = Router(name="sponsor_inquiry_referral")


# ============================================================================
# REFERRAL: Ask sponsor a question
# ============================================================================


@router.message(F.text == "💬 Написать спонсору")
async def handle_write_to_sponsor(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user: User,
    **data: Any,
) -> None:
    """Handle 'Write to Sponsor' button."""
    sponsor_service = SponsorInquiryService(session)

    # Check if user has a sponsor
    sponsor = await sponsor_service.get_user_sponsor(user.id)

    if not sponsor:
        await message.answer(
            "❌ *У вас нет спонсора*\n\n"
            "Эта функция доступна только для пользователей, "
            "которые зарегистрировались по реферальной ссылке.\n\n"
            "Если у вас есть вопросы, используйте раздел "
            "«💬 Поддержка» для связи с администрацией.",
            parse_mode="Markdown",
            reply_markup=referral_keyboard(),
        )
        return

    # Check if there's an active inquiry
    active_inquiry = await sponsor_service.get_active_inquiry_for_referral(
        user.id
    )

    if active_inquiry:
        # Show existing dialog
        sponsor_name = sponsor.username or f"ID:{sponsor.telegram_id}"
        sponsor_name = (
            sponsor_name.replace("_", "\\_")
            .replace("*", "\\*")
        )

        # Build message history
        messages_text = ""
        if active_inquiry.messages:
            for msg in active_inquiry.messages[-5:]:
                if msg.sender_type == "referral":
                    sender = "👤 Вы"
                else:
                    sender = f"👨‍💼 @{sponsor_name}"
                msg_text = msg.message_text[:100]
                if len(msg.message_text) > 100:
                    msg_text += "..."
                messages_text += f"\n{sender}: _{msg_text}_\n"

        status_text = {
            SponsorInquiryStatus.NEW.value: "⏳ Ожидает ответа",
            SponsorInquiryStatus.IN_PROGRESS.value: "💬 В процессе",
        }.get(active_inquiry.status, "")

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✍️ Написать сообщение",
                    callback_data=f"si_ref_reply:{active_inquiry.id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔚 Закрыть диалог",
                    callback_data=f"si_ref_close:{active_inquiry.id}",
                ),
            ],
        ])

        await message.answer(
            f"💬 *Диалог с @{sponsor_name}*\n\n"
            f"Статус: {status_text}\n\n"
            f"📝 *Ваш вопрос:*\n_{active_inquiry.initial_question[:150]}_\n"
            f"{messages_text}\n"
            "Выберите действие:",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

        await state.set_state(SponsorInquiryStates.in_dialog)
        await state.update_data(inquiry_id=active_inquiry.id)
        return

    # No active inquiry - prompt to write
    sponsor_name = sponsor.username or f"ID:{sponsor.telegram_id}"
    sponsor_name = sponsor_name.replace("_", "\\_").replace("*", "\\*")

    await message.answer(
        f"💬 *Написать спонсору*\n\n"
        f"Ваш спонсор: @{sponsor_name}\n\n"
        f"Напишите ваш вопрос, и он будет отправлен вашему спонсору.\n"
        f"Спонсор получит уведомление и сможет вам ответить.\n\n"
        f"📝 *Введите ваш вопрос:*\n\n"
        f"_Для отмены нажмите «📊 Главное меню»_",
        parse_mode="Markdown",
        reply_markup=referral_keyboard(),
    )
    await state.set_state(SponsorInquiryStates.writing_question)
    await state.update_data(sponsor_id=sponsor.id)


@router.message(SponsorInquiryStates.writing_question)
async def handle_referral_question_input(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user: User,
    **data: Any,
) -> None:
    """Process referral's question to sponsor."""
    from bot.utils.menu_buttons import is_menu_button

    # Check if menu button pressed
    if is_menu_button(message.text):
        await state.clear()
        return

    if not message.text or len(message.text.strip()) < 5:
        await message.answer(
            "❌ Вопрос слишком короткий. "
            "Пожалуйста, опишите ваш вопрос подробнее.",
        )
        return

    if len(message.text) > 2000:
        await message.answer(
            "❌ Вопрос слишком длинный (максимум 2000 символов). "
            "Пожалуйста, сократите текст.",
        )
        return

    question = message.text.strip()

    # Get sponsor info
    sponsor_service = SponsorInquiryService(session)
    sponsor = await sponsor_service.get_user_sponsor(user.id)

    if not sponsor:
        await state.clear()
        await message.answer(
            "❌ Ошибка: спонсор не найден.",
            reply_markup=referral_keyboard(),
        )
        return

    # Create inquiry
    inquiry = await sponsor_service.create_inquiry(
        referral_id=user.id,
        referral_telegram_id=user.telegram_id,
        sponsor_id=sponsor.id,
        sponsor_telegram_id=sponsor.telegram_id,
        question=question,
    )

    # Send notification to sponsor
    bot: Bot | None = data.get("bot")
    if bot:
        await notify_sponsor_new_inquiry(
            bot=bot,
            sponsor_telegram_id=sponsor.telegram_id,
            referral_username=user.username,
            referral_telegram_id=user.telegram_id,
            question_preview=question,
        )

    sponsor_name = sponsor.username or f"ID:{sponsor.telegram_id}"
    sponsor_name = sponsor_name.replace("_", "\\_").replace("*", "\\*")

    await state.set_state(SponsorInquiryStates.in_dialog)
    await state.update_data(inquiry_id=inquiry.id)

    await message.answer(
        f"✅ *Вопрос отправлен!*\n\n"
        f"Ваш вопрос отправлен спонсору @{sponsor_name}.\n\n"
        f"📝 *Ваш вопрос:*\n_{question[:150]}_\n\n"
        f"Вы получите уведомление, когда спонсор ответит.\n\n"
        f"💡 Вы можете продолжить диалог, нажав "
        f"«💬 Написать спонсору».",
        parse_mode="Markdown",
        reply_markup=referral_keyboard(),
    )


@router.callback_query(F.data.startswith("si_ref_reply:"))
async def handle_referral_start_reply(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    """Start referral reply to inquiry."""
    inquiry_id = int(callback.data.split(":")[1])

    await state.set_state(SponsorInquiryStates.in_dialog)
    await state.update_data(inquiry_id=inquiry_id)

    await callback.answer()
    await callback.message.answer(
        "📝 *Введите ваше сообщение:*\n\n"
        "_Для отмены нажмите «📊 Главное меню»_",
        parse_mode="Markdown",
    )


@router.message(SponsorInquiryStates.in_dialog)
async def handle_referral_dialog_message(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user: User,
    **data: Any,
) -> None:
    """Process referral's message in dialog."""
    from bot.utils.menu_buttons import is_menu_button

    if is_menu_button(message.text):
        await state.clear()
        return

    state_data = await state.get_data()
    inquiry_id = state_data.get("inquiry_id")

    if not inquiry_id:
        await state.clear()
        await message.answer(
            "❌ Ошибка: диалог не найден.",
            reply_markup=referral_keyboard(),
        )
        return

    if not message.text or len(message.text.strip()) < 1:
        await message.answer("❌ Сообщение не может быть пустым.")
        return

    msg_text = message.text.strip()[:2000]

    # Add message
    sponsor_service = SponsorInquiryService(session)
    msg = await sponsor_service.add_message(
        inquiry_id=inquiry_id,
        sender_type="referral",
        message_text=msg_text,
    )

    if not msg:
        await state.clear()
        await message.answer(
            "❌ Ошибка: диалог не найден или закрыт.",
            reply_markup=referral_keyboard(),
        )
        return

    # Notify sponsor
    inquiry = await sponsor_service.get_inquiry_by_id(inquiry_id)
    if inquiry:
        bot: Bot | None = data.get("bot")
        if bot:
            # Notify sponsor about new message (reuse similar notification)
            try:
                user_display = (
                    f"@{user.username}" if user.username
                    else f"ID:{user.telegram_id}"
                )
                await bot.send_message(
                    inquiry.sponsor_telegram_id,
                    f"💬 *Новое сообщение от реферала!*\n\n"
                    f"👤 От: {user_display}\n\n"
                    f"📝 _{msg_text[:100]}{'...' if len(msg_text) > 100 else ''}_\n\n"
                    f"Нажмите «👥 Рефералы» → «📬 Входящие от рефералов»",
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.warning(f"Failed to notify sponsor: {e}")

    await message.answer(
        "✅ Сообщение отправлено!\n\n"
        "💡 Вы получите уведомление, когда спонсор ответит.",
        reply_markup=referral_keyboard(),
    )


@router.callback_query(F.data.startswith("si_ref_close:"))
async def handle_referral_close_dialog(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    user: User,
) -> None:
    """Close dialog by referral."""
    inquiry_id = int(callback.data.split(":")[1])

    sponsor_service = SponsorInquiryService(session)
    await sponsor_service.close_inquiry(inquiry_id, "referral")

    await state.clear()
    await callback.answer("Диалог закрыт")
    await callback.message.answer(
        "✅ Диалог закрыт.\n\n"
        "Вы можете начать новый диалог, нажав «💬 Написать спонсору».",
        reply_markup=referral_keyboard(),
    )
