"""
Appeal handler.

Handles user appeals for blocked accounts.
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blacklist import BlacklistActionType
from app.models.user import User
from app.repositories.blacklist_repository import BlacklistRepository
from app.utils.datetime_utils import utc_now
from bot.keyboards.reply import main_menu_reply_keyboard
from bot.states.appeal import AppealStates


router = Router()


@router.message(F.text == "📝 Подать апелляцию")
async def start_appeal(
    message: Message,
    session: AsyncSession,
    user: User,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Start appeal process for blocked users.

    Args:
        message: Telegram message
        session: Database session
        user: Current user
        state: FSM state
    """
    # Check if user is blocked (try to get from middleware first)
    blacklist_entry = data.get("blacklist_entry")
    if blacklist_entry is None:
        blacklist_repo = BlacklistRepository(session)
        blacklist_entry = await blacklist_repo.get_by_telegram_id(user.telegram_id)

    is_admin = data.get("is_admin", False)
    if not blacklist_entry or not blacklist_entry.is_active:
        await message.answer(
            "❌ У вас нет активной блокировки для подачи апелляции.",
            reply_markup=main_menu_reply_keyboard(
                user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
            ),
        )
        return

    if blacklist_entry.action_type != BlacklistActionType.BLOCKED:
        await message.answer(
            "❌ Апелляция доступна только для заблокированных аккаунтов.",
            reply_markup=main_menu_reply_keyboard(
                user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
            ),
        )
        return

    # Check appeal deadline
    if (
        blacklist_entry.appeal_deadline
        and utc_now() > blacklist_entry.appeal_deadline
    ):
        await message.answer(
            "❌ Срок подачи апелляции истек (3 рабочих дня).",
            reply_markup=main_menu_reply_keyboard(
                user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
            ),
        )
        return

    # Check if appeal already submitted
    from app.repositories.appeal_repository import AppealRepository

    appeal_repo = AppealRepository(session)
    existing_appeal = await appeal_repo.get_active_appeal_for_user(
        user.id, blacklist_entry.id
    )

    if existing_appeal:
        created_date = existing_appeal.created_at.strftime('%d.%m.%Y %H:%M')
        await message.answer(
            "❌ У вас уже есть активная апелляция по этой блокировке.\n\n"
            f"Статус: {existing_appeal.status}\n"
            f"Подана: {created_date}\n\n"
            "Дождитесь рассмотрения текущей апелляции.",
            reply_markup=main_menu_reply_keyboard(
                user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
            ),
        )
        return

    # Check total open appeals limit
    from app.config.constants import MAX_OPEN_TICKETS_PER_USER

    open_appeals = await appeal_repo.get_active_appeals_for_user(user.id)
    if len(open_appeals) >= MAX_OPEN_TICKETS_PER_USER:
        await message.answer(
            f"❌ Превышен лимит открытых апелляций "
            f"({MAX_OPEN_TICKETS_PER_USER}). "
            "Пожалуйста, дождитесь рассмотрения существующих апелляций.",
            reply_markup=main_menu_reply_keyboard(
                user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
            ),
        )
        return

    await message.answer(
        "📝 **Подача апелляции**\n\n"
        "Опишите ситуацию и "
        "объясните, почему вы считаете блокировку несправедливой.\n\n"
        "Ваша апелляция будет рассмотрена в течение 5 рабочих дней.\n\n"
        "Введите текст апелляции:"
    )

    await state.set_state(AppealStates.waiting_for_appeal_text)


@router.message(AppealStates.waiting_for_appeal_text)
async def process_appeal_text(
    message: Message,
    session: AsyncSession,
    user: User,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Process appeal text and send to admins.

    Args:
        message: Telegram message
        session: Database session
        user: Current user
        state: FSM state
    """
    # Check if message is a menu button - if so, clear state and ignore
    from bot.utils.menu_buttons import is_menu_button

    if message.text and is_menu_button(message.text):
        await state.clear()
        return  # Let menu handlers process this

    # Validate message text exists
    if not message.text:
        await message.answer("❌ Пожалуйста, введите текст апелляции.")
        return

    appeal_text = message.text.strip()

    if len(appeal_text) < 20:
        await message.answer(
            "❌ Текст апелляции слишком короткий. "
            "Минимум 20 символов. Попробуйте еще раз:"
        )
        return

    # Get blacklist entry (try to get from middleware first)
    blacklist_entry = data.get("blacklist_entry")
    if blacklist_entry is None:
        blacklist_repo = BlacklistRepository(session)
        blacklist_entry = await blacklist_repo.get_by_telegram_id(user.telegram_id)

    if not blacklist_entry:
        is_admin = data.get("is_admin", False)
        await message.answer(
            "❌ Ошибка: запись о блокировке не найдена.",
            reply_markup=main_menu_reply_keyboard(
                user=user, blacklist_entry=None, is_admin=is_admin
            ),
        )
        await state.clear()
        return

    # Create appeal record in database
    from app.models.appeal import AppealStatus
    from app.repositories.appeal_repository import AppealRepository

    appeal_repo = AppealRepository(session)
    appeal = await appeal_repo.create(
        user_id=user.id,
        blacklist_id=blacklist_entry.id,
        appeal_text=appeal_text,
        status=AppealStatus.PENDING,
    )

    await session.flush()  # Flush to get appeal.id

    # Create support ticket for appeal (for admin notification)
    from app.models.enums import (
        SupportCategory,
        SupportTicketPriority,
        SupportTicketStatus,
    )
    from app.repositories.support_ticket_repository import (
        SupportTicketRepository,
    )

    ticket_repo = SupportTicketRepository(session)

    # Format dates for display
    blocked_date = blacklist_entry.created_at.strftime('%Y-%m-%d %H:%M:%S')
    deadline_date = (
        blacklist_entry.appeal_deadline.strftime('%Y-%m-%d %H:%M:%S')
        if blacklist_entry.appeal_deadline
        else 'N/A'
    )

    appeal_ticket = await ticket_repo.create(
        user_id=user.id,
        category=SupportCategory.OTHER.value,
        priority=SupportTicketPriority.HIGH.value,
        status=SupportTicketStatus.OPEN.value,
        subject=(
            f"Апелляция по блокировке аккаунта (User ID: "
            f"{user.id}, Appeal ID: {appeal.id})"
        ),
        description=(
            f"**Апелляция от пользователя:**\n"
            f"Telegram ID: {user.telegram_id}\n"
                f"Username: @{user.username or 'N/A'}\n"
                f"Wallet: {user.wallet_address}\n\n"
                f"**Текст апелляции:**\n{appeal_text}\n\n"
                f"**Информация о блокировке:**\n"
                f"Причина: {blacklist_entry.reason or 'Не указана'}\n"
                f"Дата блокировки: {blocked_date}\n"
                f"Срок подачи апелляции: {deadline_date}"
        ),
    )

    await session.commit()

    logger.info(
        "Appeal submitted",
        extra={
            "user_id": user.id,
            "telegram_id": user.telegram_id,
            "appeal_id": appeal.id,
            "blacklist_id": blacklist_entry.id,
            "ticket_id": appeal_ticket.id,
        },
    )

    is_admin = data.get("is_admin", False)
    await message.answer(
        "✅ **Апелляция подана!**\n\n"
        f"🆔 ID апелляции: #{appeal.id}\n"
        f"📋 Номер обращения: #{appeal_ticket.id}\n\n"
        "Ваша апелляция будет рассмотрена в течение 5 рабочих дней.\n"
        "Вы получите уведомление о результате рассмотрения.",
        reply_markup=main_menu_reply_keyboard(
            user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
        ),
    )

    await state.clear()
