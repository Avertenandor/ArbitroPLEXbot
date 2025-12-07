"""
Help submenu handlers.

This module contains handlers for the help submenu, which includes:
- FAQ
- Instructions
- Rules
- Support contact
- Back navigation to main menu
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.support_service import SupportService
from bot.keyboards.user import help_submenu_keyboard
from bot.states.support_states import SupportStates
from bot.utils.user_loader import UserLoader

router = Router()


@router.message(StateFilter('*'), F.text == "💬 Помощь")
async def show_help_submenu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Show help submenu.

    Args:
        message: Message object
        session: Database session
        state: FSM state
        **data: Handler data (includes user from AuthMiddleware)
    """
    telegram_id = message.from_user.id if message.from_user else None
    logger.info(f"[SUBMENU] Help submenu requested by user {telegram_id}")

    user: User | None = data.get("user")
    if not user and telegram_id:
        user = await UserLoader.get_user_by_telegram_id(session, telegram_id)
    if not user:
        await message.answer(
            "⚠️ Ошибка: не удалось загрузить данные пользователя. "
            "Попробуйте отправить /start"
        )
        return

    await state.clear()

    text = (
        "💬 *Помощь и поддержка*\n\n"
        "Здесь вы найдете всю необходимую информацию:\n\n"
        "❓ *FAQ* — ответы на частые вопросы\n"
        "📖 *Инструкции* — как пользоваться ботом\n"
        "📋 *Правила* — правила платформы\n"
        "✉️ *Написать в поддержку* — связаться с администрацией\n\n"
        "Выберите нужный раздел:"
    )

    await message.answer(
        text,
        reply_markup=help_submenu_keyboard(),
        parse_mode="Markdown"
    )
    logger.info(f"[SUBMENU] Help submenu shown to user {telegram_id}")


@router.message(StateFilter('*'), F.text == "❓ FAQ")
async def show_faq(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Show FAQ (Frequently Asked Questions).

    Args:
        message: Message object
        session: Database session
        state: FSM state
        **data: Handler data (includes user from AuthMiddleware)
    """
    telegram_id = message.from_user.id if message.from_user else None
    logger.info(f"[FAQ] FAQ requested by user {telegram_id}")

    await state.clear()

    faq_text = (
        "❓ *Часто задаваемые вопросы (FAQ)*\n\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "*1. Как начать работу с ботом?*\n"
        "• Пройдите регистрацию через /start\n"
        "• Привяжите BSC кошелек\n"
        "• Создайте финансовый пароль\n"
        "• Сделайте тестовый депозит\n\n"
        "*2. Какие уровни депозитов доступны?*\n"
        "• 🎯 Тестовый: $30 - $100\n"
        "• 💰 Уровень 1: $100 - $500\n"
        "• 💎 Уровень 2: $700 - $1,200\n"
        "• 🏆 Уровень 3: $1,400 - $2,200\n"
        "• 👑 Уровень 4: $2,500 - $3,500\n"
        "• 🚀 Уровень 5: $4,000 - $7,000\n\n"
        "*3. Что такое PLEX оплата?*\n"
        "PLEX — токен для оплаты работы депозитов.\n"
        "Требуется: 10 PLEX за каждый $1 депозита в сутки.\n\n"
        "*4. Как вывести средства?*\n"
        "• Перейдите в раздел «💸 Вывод»\n"
        "• Укажите сумму или выведите все\n"
        "• Подтвердите операцию финпаролем\n\n"
        "*5. Что такое финпароль?*\n"
        "Финансовый пароль защищает ваши средства.\n\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "💡 Не нашли ответ? Используйте «✉️ Написать в поддержку»"
    )

    await message.answer(
        faq_text,
        reply_markup=help_submenu_keyboard(),
        parse_mode="Markdown"
    )
    logger.info(f"[FAQ] FAQ shown to user {telegram_id}")


@router.message(StateFilter('*'), F.text == "✉️ Написать в поддержку")
async def show_support_contact(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Show support contact options.

    Args:
        message: Message object
        session: Database session
        state: FSM state
        **data: Handler data (includes user from AuthMiddleware)
    """
    telegram_id = message.from_user.id if message.from_user else None
    logger.info(f"[SUPPORT] Support contact requested by user {telegram_id}")

    await state.clear()

    text = (
        "✉️ *Связь с поддержкой*\n\n"
        "Вы можете связаться с нашей службой поддержки несколькими способами:\n\n"
        "1️⃣ *Создать обращение в боте*\n"
        "Используйте кнопку ниже для создания обращения прямо в боте. "
        "Администрация ответит вам в течение 24 часов.\n\n"
        "2️⃣ *Связаться напрямую*\n"
        "Напишите администратору @PlexArbitrage\\_support\n\n"
        "⏰ Время работы поддержки: ежедневно, 24/7\n"
        "⚡ Среднее время ответа: 1-3 часа"
    )

    # Add inline keyboard with support options
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✉️ Создать обращение",
            callback_data="support:create_inquiry"
        )],
        [InlineKeyboardButton(
            text="📋 Мои обращения",
            callback_data="support:my_inquiries"
        )],
    ])

    await message.answer(
        text,
        reply_markup=kb,
        parse_mode="Markdown"
    )

    # Send back button with reply keyboard
    await message.answer(
        "⬅️ Для возврата в меню помощи:",
        reply_markup=help_submenu_keyboard()
    )
    logger.info(f"[SUPPORT] Support contact shown to user {telegram_id}")


@router.callback_query(F.data == "support:create_inquiry")
async def callback_create_inquiry(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Handle callback for creating support inquiry.

    Args:
        callback: Callback query object
        session: Database session
        state: FSM state
        **data: Handler data (includes user from AuthMiddleware)
    """
    telegram_id = callback.from_user.id if callback.from_user else None
    logger.info(f"[SUPPORT] Create inquiry callback from user {telegram_id}")

    if not telegram_id:
        await callback.answer(
            "❌ Системная ошибка. Отправьте /start или попробуйте позже.",
            show_alert=True
        )
        return

    # Answer callback to remove loading state
    await callback.answer()

    text = (
        "✉️ *Создать обращение*\n\n"
        "Опишите вашу проблему или вопрос.\n"
        "Отправьте текстовое сообщение.\n\n"
        "💡 **Совет:** Если вопрос касается финансов, укажите:\n"
        "• ID транзакции (Hash)\n"
        "• Сумму и дату\n\n"
        "Для отмены нажмите '📊 Главное меню'"
    )

    await state.set_state(SupportStates.awaiting_input)

    # Edit the message or send new one
    if callback.message:
        await callback.message.answer(text, parse_mode="Markdown")

    logger.info(f"[SUPPORT] User {telegram_id} entered ticket creation state")


@router.callback_query(F.data == "support:my_inquiries")
async def callback_my_inquiries(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Handle callback for viewing user's support inquiries.

    Args:
        callback: Callback query object
        session: Database session
        state: FSM state
        **data: Handler data (includes user from AuthMiddleware)
    """
    user: User | None = data.get("user")
    telegram_id = callback.from_user.id if callback.from_user else None
    logger.info(f"[SUPPORT] My inquiries callback from user {telegram_id}")

    if not telegram_id:
        await callback.answer(
            "❌ Системная ошибка. Отправьте /start или попробуйте позже.",
            show_alert=True
        )
        return

    # Answer callback to remove loading state
    await callback.answer()

    session_factory = data.get("session_factory")

    # Get tickets using appropriate method
    if not session_factory:
        # Fallback to old session
        support_service = SupportService(session)
        if user:
            tickets = await support_service.get_user_tickets(user.id)
        else:
            # Guest tickets
            tickets = await support_service.get_guest_tickets(telegram_id)
    else:
        # NEW pattern: short read transaction
        async with session_factory() as session:
            async with session.begin():
                support_service = SupportService(session)
                if user:
                    tickets = await support_service.get_user_tickets(user.id)
                else:
                    # Guest tickets
                    tickets = await support_service.get_guest_tickets(telegram_id)
        # Transaction closed here

    # Format response
    if not tickets:
        if user is None:
            text = (
                "📋 *Мои обращения*\n\n"
                "У вас пока нет обращений.\n\n"
                "Для создания обращения используйте кнопку '✉️ Создать обращение'."
            )
        else:
            text = "📋 У вас пока нет обращений"
    else:
        text = "📋 *Ваши обращения:*\n\n"

        for ticket in tickets[:10]:  # Show last 10
            status_emoji = {
                "open": "🔵",
                "in_progress": "🟡",
                "answered": "🟢",
                "closed": "⚫",
            }.get(ticket.status, "⚪")

            created_date = ticket.created_at.strftime('%d.%m.%Y %H:%M')
            subject = getattr(ticket, 'subject', 'Обращение')
            # Add "(Гость)" marker for guest tickets
            guest_marker = " (Гость)" if user is None else ""
            text += (
                f"{status_emoji} #{ticket.id} - {subject}{guest_marker}\n"
                f"   Создано: {created_date}\n\n"
            )

    # Send response
    if callback.message:
        await callback.message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=help_submenu_keyboard()
        )

    logger.info(f"[SUPPORT] Showed {len(tickets) if tickets else 0} tickets to user {telegram_id}")
