"""
Sponsor Inquiry Handlers - Sponsor Side.

Handles sponsor's incoming questions from referrals.
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
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sponsor_inquiry import SponsorInquiryStatus
from app.models.user import User
from app.services.sponsor_inquiry_service import (
    SponsorInquiryService,
    notify_referral_sponsor_reply,
)
from bot.keyboards.reply import referral_keyboard
from bot.states.sponsor_inquiry import SponsorInquiryStates

router = Router(name="sponsor_inquiry_sponsor")


# ============================================================================
# SPONSOR: View incoming inquiries
# ============================================================================


@router.message(F.text == "📬 Входящие от рефералов")
async def handle_sponsor_inbox(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user: User,
    **data: Any,
) -> None:
    """Show sponsor's incoming inquiries from referrals."""
    sponsor_service = SponsorInquiryService(session)

    # Get active inquiries
    inquiries = await sponsor_service.get_active_inquiries_for_sponsor(user.id)
    unread_count = await sponsor_service.get_unread_count_for_sponsor(user.id)

    if not inquiries:
        await message.answer(
            "📬 *Входящие от рефералов*\n\n"
            "У вас пока нет вопросов от ваших рефералов.\n\n"
            "💡 Когда кто-то из ваших партнёров задаст вопрос, "
            "вы получите уведомление.",
            parse_mode="Markdown",
            reply_markup=referral_keyboard(),
        )
        return

    # Build inquiry list
    text = "📬 *Входящие от рефералов*\n\n"

    if unread_count > 0:
        text += f"🔴 Новых сообщений: *{unread_count}*\n\n"

    # Create inline buttons for each inquiry
    buttons = []
    for inq in inquiries[:10]:  # Limit to 10
        referral = inq.referral
        ref_name = referral.username or f"ID:{referral.telegram_id}"
        ref_name = ref_name[:15]

        # Status indicator
        if not inq.is_read_by_sponsor:
            indicator = "🔴"
        elif inq.status == SponsorInquiryStatus.NEW.value:
            indicator = "🆕"
        else:
            indicator = "💬"

        # Question preview
        question_preview = inq.initial_question[:30]
        if len(inq.initial_question) > 30:
            question_preview += "..."

        buttons.append([
            InlineKeyboardButton(
                text=f"{indicator} @{ref_name}: {question_preview}",
                callback_data=f"si_sponsor_view:{inq.id}",
            )
        ])

        text += (
            f"{indicator} *@{ref_name}*\n"
            f"   _{question_preview}_\n\n"
        )

    buttons.append([
        InlineKeyboardButton(
            text="📜 История диалогов",
            callback_data="si_sponsor_history",
        )
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

    await state.set_state(SponsorInquiryStates.viewing_inquiries)


@router.callback_query(F.data.startswith("si_sponsor_view:"))
async def handle_sponsor_view_inquiry(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    user: User,
    **data: Any,
) -> None:
    """View specific inquiry."""
    inquiry_id = int(callback.data.split(":")[1])

    sponsor_service = SponsorInquiryService(session)
    inquiry = await sponsor_service.get_inquiry_by_id(inquiry_id)

    if not inquiry or inquiry.sponsor_id != user.id:
        await callback.answer("Диалог не найден")
        return

    # Mark as read
    await sponsor_service.mark_as_read_by_sponsor(inquiry_id)

    referral = inquiry.referral
    ref_name = referral.username or f"ID:{referral.telegram_id}"
    ref_name_escaped = (
        ref_name.replace("_", "\\_")
        .replace("*", "\\*")
        .replace("`", "\\`")
    )

    # Build message history
    text = f"💬 *Диалог с @{ref_name_escaped}*\n\n"
    text += f"📝 *Исходный вопрос:*\n_{inquiry.initial_question[:300]}_\n\n"

    if inquiry.messages and len(inquiry.messages) > 1:
        text += "📜 *История:*\n"
        for msg in inquiry.messages[-5:]:
            if msg.sender_type == "referral":
                sender = f"👤 @{ref_name_escaped}"
            else:
                sender = "👨‍💼 Вы"

            msg_text = msg.message_text[:150]
            if len(msg.message_text) > 150:
                msg_text += "..."

            time_str = msg.created_at.strftime("%d.%m %H:%M")
            text += f"\n{sender} ({time_str}):\n_{msg_text}_\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✍️ Ответить",
                callback_data=f"si_sponsor_reply:{inquiry_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔚 Закрыть диалог",
                callback_data=f"si_sponsor_close:{inquiry_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="◀️ Назад к списку",
                callback_data="si_sponsor_back",
            ),
        ],
    ])

    await callback.answer()
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

    await state.update_data(inquiry_id=inquiry_id)


@router.callback_query(F.data.startswith("si_sponsor_reply:"))
async def handle_sponsor_start_reply(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    """Start sponsor reply to inquiry."""
    inquiry_id = int(callback.data.split(":")[1])

    await state.set_state(SponsorInquiryStates.replying)
    await state.update_data(inquiry_id=inquiry_id)

    await callback.answer()
    await callback.message.answer(
        "✍️ *Введите ваш ответ:*\n\n"
        "_Для отмены нажмите «📊 Главное меню»_",
        parse_mode="Markdown",
    )


@router.message(SponsorInquiryStates.replying)
async def handle_sponsor_reply_input(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user: User,
    **data: Any,
) -> None:
    """Process sponsor's reply."""
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

    reply_text = message.text.strip()[:2000]

    # Add message
    sponsor_service = SponsorInquiryService(session)
    msg = await sponsor_service.add_message(
        inquiry_id=inquiry_id,
        sender_type="sponsor",
        message_text=reply_text,
    )

    if not msg:
        await state.clear()
        await message.answer(
            "❌ Ошибка: диалог не найден или закрыт.",
            reply_markup=referral_keyboard(),
        )
        return

    # Notify referral
    inquiry = await sponsor_service.get_inquiry_by_id(inquiry_id)
    if inquiry:
        bot: Bot | None = data.get("bot")
        if bot:
            await notify_referral_sponsor_reply(
                bot=bot,
                referral_telegram_id=inquiry.referral_telegram_id,
                sponsor_username=user.username,
                reply_preview=reply_text,
            )

    await state.clear()
    await message.answer(
        "✅ *Ответ отправлен!*\n\n"
        "Ваш реферал получит уведомление о вашем ответе.\n\n"
        "💡 Нажмите «📬 Входящие от рефералов» чтобы посмотреть все диалоги.",
        parse_mode="Markdown",
        reply_markup=referral_keyboard(),
    )


@router.callback_query(F.data.startswith("si_sponsor_close:"))
async def handle_sponsor_close_dialog(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    user: User,
) -> None:
    """Close dialog by sponsor."""
    inquiry_id = int(callback.data.split(":")[1])

    sponsor_service = SponsorInquiryService(session)
    await sponsor_service.close_inquiry(inquiry_id, "sponsor")

    await state.clear()
    await callback.answer("Диалог закрыт")
    await callback.message.answer(
        "✅ Диалог закрыт.\n\n"
        "Реферал сможет начать новый диалог, если у него возникнут вопросы.",
        reply_markup=referral_keyboard(),
    )


@router.callback_query(F.data == "si_sponsor_back")
async def handle_sponsor_back_to_list(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    user: User,
    **data: Any,
) -> None:
    """Go back to inquiry list."""
    await callback.answer()

    # Simulate pressing the inbox button
    sponsor_service = SponsorInquiryService(session)
    inquiries = await sponsor_service.get_active_inquiries_for_sponsor(user.id)
    unread_count = await sponsor_service.get_unread_count_for_sponsor(user.id)

    if not inquiries:
        await callback.message.edit_text(
            "📬 *Входящие от рефералов*\n\n"
            "У вас пока нет вопросов от ваших рефералов.",
            parse_mode="Markdown",
        )
        return

    # Build inquiry list
    text = "📬 *Входящие от рефералов*\n\n"

    if unread_count > 0:
        text += f"🔴 Новых сообщений: *{unread_count}*\n\n"

    buttons = []
    for inq in inquiries[:10]:
        referral = inq.referral
        ref_name = referral.username or f"ID:{referral.telegram_id}"
        ref_name = ref_name[:15]

        if not inq.is_read_by_sponsor:
            indicator = "🔴"
        elif inq.status == SponsorInquiryStatus.NEW.value:
            indicator = "🆕"
        else:
            indicator = "💬"

        question_preview = inq.initial_question[:30]
        if len(inq.initial_question) > 30:
            question_preview += "..."

        buttons.append([
            InlineKeyboardButton(
                text=f"{indicator} @{ref_name}: {question_preview}",
                callback_data=f"si_sponsor_view:{inq.id}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="📜 История диалогов",
            callback_data="si_sponsor_history",
        )
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "si_sponsor_history")
async def handle_sponsor_history(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
) -> None:
    """Show sponsor's inquiry history."""
    sponsor_service = SponsorInquiryService(session)
    history = await sponsor_service.get_inquiry_history_for_sponsor(
        user.id, limit=15
    )

    if not history:
        await callback.answer("История пуста")
        return

    text = "📜 *История диалогов*\n\n"

    for inq in history:
        referral = inq.referral
        ref_name = referral.username or f"ID:{referral.telegram_id}"
        ref_name = ref_name[:15].replace("_", "\\_")

        status_emoji = {
            SponsorInquiryStatus.NEW.value: "🆕",
            SponsorInquiryStatus.IN_PROGRESS.value: "💬",
            SponsorInquiryStatus.CLOSED.value: "✅",
        }.get(inq.status, "❓")

        date_str = inq.created_at.strftime("%d.%m.%Y")
        question_preview = inq.initial_question[:40]
        if len(inq.initial_question) > 40:
            question_preview += "..."

        text += (
            f"{status_emoji} *@{ref_name}* ({date_str})\n"
            f"   _{question_preview}_\n\n"
        )

    text += "_✅ = закрыт, 💬 = активен, 🆕 = новый_"

    await callback.answer()
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="◀️ Назад",
                    callback_data="si_sponsor_back",
                )
            ]
        ]),
    )
